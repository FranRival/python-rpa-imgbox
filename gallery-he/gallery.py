#!/usr/bin/env python3
"""
respaldar_media.py - Alternativa ligera a JDownloader.

Lee una lista de URLs (urls.txt), busca todos los archivos media dentro de
cada página (imágenes, videos, audio, PDFs, etc.) y los guarda en local.

Instalación:
    pip install requests beautifulsoup4

Uso:
    python respaldar_media.py                      # usa urls.txt -> carpeta respaldo/
    python respaldar_media.py -i mis_urls.txt -o D:/respaldo -w 6
    python respaldar_media.py --originales         # WordPress: baja la imagen sin -300x200
    python respaldar_media.py --paginar --prueba   # recorre ?p=1,2,3... y solo lista (sin descargar)
    python respaldar_media.py --paginar --sitio "midominio.com/s/"
    python respaldar_media.py --paginar --selector-detalle "img#foto"   # señalar la imagen grande exacta
    python respaldar_media.py --fuente pagina.html     # código fuente guardado (como pegarlo en JDownloader)
    python respaldar_media.py --fuente carpeta_html/ --base-url https://tusitio.com
    python respaldar_media.py --diagnostico URL_IMAGEN --pagina URL_PAGINA   # ¿qué protección hay?
    python respaldar_media.py --cabeceras-archivo cabeceras.txt            # usar las cabeceras de tu navegador
    python respaldar_media.py --ytdlp              # además intenta videos de YouTube/Vimeo/etc.
                                                   # (requiere: pip install yt-dlp)

urls.txt: una URL por línea. Las líneas que empiezan con # se ignoran.
Es reanudable: si lo vuelves a correr, salta lo que ya se descargó.
"""

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======================= CONFIGURACIÓN =======================
# SITIO: filtro para localizar las páginas de detalle que hay que visitar.
# Se visitan todas las URLs de la página (con o sin <img>, enlaces o JavaScript) que
# CONTENGAN este texto. Ejemplos:
#     SITIO = "/s/"                  -> cualquier URL con /s/ del mismo sitio
#     SITIO = "midominio.com/s/"     -> solo URLs de ese dominio con /s/
#     SITIO = ""                     -> (sin filtro) enlaces que traigan miniatura
# También se puede cambiar al ejecutar:  --sitio "midominio.com/s/"
SITIO = "/s/"
# =============================================================

MEDIA_EXT = {
    # imagen
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".bmp", ".tiff", ".ico",
    # video
    ".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4v", ".flv", ".wmv", ".m3u8",
    # audio
    ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".opus",
    # documentos
    ".pdf", ".zip", ".rar", ".7z",
}

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

CHUNK = 256 * 1024  # 256 KB: se escribe a disco por partes, RAM mínima
WP_SIZE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[a-zA-Z0-9]+$)")

ATRIBUTOS_SRC = (
    "src", "data-src", "data-lazy-src", "data-original", "poster", "data-full-url",
    "data-full", "data-large", "data-large_image", "data-zoom-image",
    "data-orig-file", "data-large-file", "data-image", "data-bg",
)
# atributos que suelen apuntar a la versión grande
ATRIBUTOS_GRANDES = {
    "data-full", "data-large", "data-large_image", "data-zoom-image",
    "data-orig-file", "data-large-file", "data-full-url", "data-original",
}
EXT_NO_MEDIA = {".html", ".htm", ".php", ".asp", ".aspx", ".js", ".css", ".json", ".xml", ".txt"}
TRACKERS = re.compile(r"(facebook\.com/tr|google-analytics|googletagmanager|doubleclick|/pixel|1x1|spacer\.gif)", re.I)
CT_EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "image/avif": ".avif", "image/svg+xml": ".svg", "image/bmp": ".bmp",
    "image/tiff": ".tiff", "video/mp4": ".mp4", "video/webm": ".webm", "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg", "audio/wav": ".wav", "application/pdf": ".pdf",
}
PISTAS_BUENAS = re.compile(r"(main|full|large|big|grande|principal|hero|zoom|original|photo|foto|imagen|image)", re.I)
PISTAS_MALAS = re.compile(r"(thumb|small|mini|icon|logo|avatar|sprite|banner|placeholder|loader|blank|pixel|emoji|share|related|relacionad)", re.I)


REFERER_FIJO = ""  # se llena con --referer


def describir_error(e: Exception) -> str:
    """Convierte un error de requests en un mensaje con la causa probable."""
    resp = getattr(e, "response", None)
    if isinstance(e, requests.HTTPError) and resp is not None:
        c = resp.status_code
        server = resp.headers.get("Server", "")
        extra = f" (servidor: {server})" if server else ""
        pistas = {
            401: "requiere autenticación (cookie de sesión o cabecera Authorization): usa --cabeceras-archivo o --cookie",
            403: "acceso denegado: suele ser Referer/anti-hotlink, cookie o protección tipo Cloudflare. "
                 "Prueba: --diagnostico URL_DE_LA_IMAGEN",
            404: "esa URL no existe",
            429: "demasiadas peticiones: baja las descargas simultáneas con -w 1",
        }
        return f"HTTP {c}{extra}: {pistas.get(c, 'respuesta inesperada')}"
    return str(e)


def leer_cabeceras(ruta: Path) -> dict[str, str]:
    """Lee cabeceras desde un archivo: acepta un comando "Copy as cURL (bash)" pegado tal cual
    o líneas "Nombre: valor"."""
    texto = ruta.read_text(encoding="utf-8", errors="ignore").replace("\\\n", " ")
    cab: dict[str, str] = {}
    for m in re.finditer(r"""(?:-H|--header)\s+(['"])(.*?)\1""", texto, re.S):
        nombre, _, valor = m.group(2).partition(":")
        if nombre.strip():
            cab[nombre.strip()] = valor.strip()
    for m in re.finditer(r"""(?:-b|--cookie)\s+(['"])(.*?)\1""", texto, re.S):
        cab["Cookie"] = m.group(2).strip()
    if not cab:  # formato línea por línea
        for linea in texto.splitlines():
            n, _, v = linea.partition(":")
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9\-]*", n.strip()) and not linea.lstrip().startswith("curl"):
                cab[n.strip()] = v.strip()
    # estas rompen requests (br/zstd no se decodifican, 304, host propio...) o se manejan aparte
    prohibidas = {"host", "content-length", "accept-encoding", "connection", "if-none-match",
                  "if-modified-since", "referer", "range"}
    return {k: v for k, v in cab.items() if k.lower() not in prohibidas and not k.startswith(":")}


def configurar_sesion(sesion: requests.Session, args) -> None:
    global REFERER_FIJO
    REFERER_FIJO = args.referer or ""
    if args.user_agent:
        sesion.headers["User-Agent"] = args.user_agent
    if args.cabeceras_archivo:
        ruta = Path(args.cabeceras_archivo).expanduser()
        if ruta.is_file():
            cab = leer_cabeceras(ruta)
            sesion.headers.update(cab)
            print(f"Cabeceras importadas de {ruta.name}: {', '.join(sorted(cab)) or '(ninguna)'}")
        else:
            print(f"(no existe {ruta}, no se importan cabeceras)")
    for h in args.header or []:
        n, _, v = h.partition(":")
        if n.strip():
            sesion.headers[n.strip()] = v.strip()
    if args.cookie:
        sesion.headers["Cookie"] = args.cookie


def diagnostico(sesion: requests.Session, url_img: str, url_pagina: str = "") -> None:
    """Prueba la descarga de UNA imagen con distintas cabeceras y dice qué protección hay."""
    p = urlparse(url_img)
    raiz = f"{p.scheme}://{p.netloc}/"
    print(f"DIAGNÓSTICO\n  imagen: {url_img}")
    if url_pagina:
        try:
            r = sesion.get(url_pagina, timeout=30)
            bajo = r.text.lower()
            reto = any(m in bajo for m in ("just a moment", "cf-chl", "attention required",
                                           "cf-browser-verification", "captcha"))
            print(f"  página: HTTP {r.status_code} | {len(r.content) // 1024} KB | servidor={r.headers.get('Server', '?')}"
                  + ("  <- parece una pantalla de verificación (Cloudflare/captcha)" if reto else ""))
        except Exception as e:  # noqa: BLE001
            print(f"  página: ERROR {describir_error(e)}")

    ref = url_pagina or raiz
    pruebas = [("Sin Referer", {})]
    if url_pagina:
        pruebas.append(("Referer = la página del sitio", {"Referer": url_pagina}))
    pruebas.append(("Referer = raíz del sitio", {"Referer": raiz}))
    pruebas.append(("Referer + cabeceras de navegador", {
        "Referer": ref, "Sec-Fetch-Dest": "image", "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}))

    resultados = []
    print("  pruebas:")
    for nombre, h in pruebas:
        try:
            r = sesion.get(url_img, stream=True, timeout=30, headers=h)
            ct = r.headers.get("Content-Type", "?").split(";")[0].strip()
            extra = " | ".join(f"{k}={r.headers[k]}" for k in
                               ("Server", "CF-Ray", "cf-mitigated", "WWW-Authenticate") if k in r.headers)
            print(f"    {nombre:36} -> HTTP {r.status_code} | {ct} | {r.headers.get('Content-Length', '?')} bytes"
                  + (f" | {extra}" if extra else ""))
            resultados.append((nombre, r.status_code, ct, r.headers))
            r.close()
        except Exception as e:  # noqa: BLE001
            print(f"    {nombre:36} -> ERROR {e}")
            resultados.append((nombre, 0, "", {}))

    es_media = lambda ct: ct.startswith(("image/", "video/", "audio/")) or ct in ("application/octet-stream", "application/pdf")
    buenos = [n for n, st, ct, _ in resultados if st == 200 and es_media(ct)]
    estados = {st for _, st, _, _ in resultados}
    cf = any("cf-ray" in {k.lower() for k in hd} for *_, hd in resultados)
    print("\n  CONCLUSIÓN:")
    if buenos and buenos[0] == "Sin Referer":
        print("    Sin protección por cabeceras: la imagen se descarga normal. Si el script falla, revisa errores.txt.")
    elif buenos:
        print(f"    Hay protección por Referer: funciona con '{buenos[0]}'. El script ya envía la página como "
              "Referer; si falla, fuerza uno con --referer https://tusitio.com/")
    elif 401 in estados:
        print("    Pide autenticación (401): necesitas la cookie de sesión o la cabecera Authorization de tu navegador.\n"
              "    Usa --cabeceras-archivo (ver instrucciones) o --cookie.")
    elif 403 in estados and cf:
        print("    Cloudflare está bloqueando al script (403). Usa --cabeceras-archivo con las cabeceras y cookies de tu\n"
              "    navegador (incluida cf_clearance) y el mismo User-Agent.")
    elif 403 in estados:
        print("    Acceso denegado (403) sin importar el Referer: probablemente cookie de sesión o User-Agent/cabeceras.\n"
              "    Usa --cabeceras-archivo con las de tu navegador.")
    else:
        print(f"    Estados recibidos: {sorted(estados)}. Revisa que la URL de la imagen sea correcta.")


def crear_sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def html_de(r: requests.Response) -> str:
    """Texto HTML con la codificación correcta (requests asume latin-1 si el servidor
    no declara charset, lo que rompe acentos y ñ en los títulos)."""
    if "charset" not in r.headers.get("Content-Type", "").lower():
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def slug(texto: str, maximo: int = 80) -> str:
    texto = re.sub(r"[^\w.\-]+", "_", texto, flags=re.UNICODE).strip("_")
    return texto[:maximo] or "pagina"


def carpeta_para_url(base: Path, url: str) -> Path:
    p = urlparse(url)
    nombre = slug(p.netloc + p.path)
    if p.query:
        nombre += "_" + hashlib.md5(p.query.encode()).hexdigest()[:6]
    return base / nombre


def carpeta_para_pagina(base: Path, url: str, html: str, usar_titulo: bool) -> Path:
    """Nombra la carpeta con el h1 (o title) de la página; si no hay, usa la URL.
    Se añade un hash corto de la URL para evitar choques entre títulos iguales."""
    if usar_titulo:
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        texto = h1.get_text(" ", strip=True) if h1 else ""
        if not texto and soup.title and soup.title.string:
            texto = soup.title.string.strip()
        if texto:
            return base / f"{slug(texto, 70)}_{hashlib.md5(url.encode()).hexdigest()[:6]}"
    return carpeta_para_url(base, url)


def extension(url: str) -> str:
    return Path(unquote(urlparse(url).path)).suffix.lower()


def mejor_de_srcset(srcset: str) -> str | None:
    """Devuelve la URL de mayor resolución de un atributo srcset."""
    mejor, mejor_w = None, -1
    for parte in srcset.split(","):
        trozos = parte.strip().split()
        if not trozos:
            continue
        w = 0
        if len(trozos) > 1 and trozos[1][:-1].replace(".", "").isdigit():
            w = float(trozos[1][:-1])
        if w >= mejor_w:
            mejor, mejor_w = trozos[0], w
    return mejor


_EXT = "|".join(sorted((e[1:] for e in MEDIA_EXT), key=len, reverse=True))
_FIN = r"""\s"'<>()\\\[\]{}|^`"""  # caracteres que terminan una URL
RE_ABS = re.compile(
    r"(?:https?:)?//[^" + _FIN + r"]+?\.(?:" + _EXT + r")(?:\?[^" + _FIN + r"]*)?(?=[" + _FIN + r",;]|$)",
    re.I,
)
RE_REL = re.compile(
    r"""["'(=]\s*((?:\.{0,2}/)?[^""" + _FIN + r"""]+?\.(?:""" + _EXT + r""")(?:\?[^""" + _FIN + r"""]*)?)(?=["')\s])""",
    re.I,
)


def normalizar_texto(t: str) -> str:
    """Deshace escapes típicos de barras, ampersands y comillas para que las URLs queden legibles."""
    t = t.replace("\\/", "/")
    t = re.sub(r"\\u002[fF]", "/", t)
    t = re.sub(r"\\x2[fF]", "/", t)
    t = re.sub(r"\\u0026", "&", t)
    return unescape(t)


def extraer_urls_texto(texto: str, base_url: str, originales: bool = False) -> set[str]:
    """Como el capturador de JDownloader: escanea TODO el texto (HTML, CSS, JS, JSON,
    atributos raros) buscando cualquier URL que termine en una extensión de media."""
    t = normalizar_texto(texto)
    crudas = [m.group(0) for m in RE_ABS.finditer(t)] + [m.group(1) for m in RE_REL.finditer(t)]
    res: set[str] = set()
    for c in crudas:
        u = urljoin(base_url, c.strip()).split("#")[0]
        if not u.startswith(("http://", "https://")) or extension(u) not in MEDIA_EXT:
            continue
        res.add(WP_SIZE.sub("", u) if originales else u)
    return res


def inferir_base(html: str) -> str:
    """URL original de un código fuente guardado (<base>, canonical u og:url)."""
    soup = BeautifulSoup(html, "html.parser")
    b = soup.find("base", href=True)
    if b and b["href"].startswith("http"):
        return b["href"]
    c = soup.find("link", rel="canonical", href=True)
    if c and c["href"].startswith("http"):
        return c["href"]
    m = soup.find("meta", attrs={"property": "og:url"})
    if m and (m.get("content") or "").startswith("http"):
        return m["content"]
    return ""


def extraer_media_estructura(html: str, base_url: str, originales: bool) -> set[str]:
    """Solo lo que se ve por etiquetas (para comparar en el diagnóstico)."""
    return extraer_media(html, base_url, originales, con_texto=False)


def extraer_media(html: str, base_url: str, originales: bool, con_texto: bool = True) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidatos: set[str] = set()

    for tag in soup.find_all(["img", "video", "audio", "source", "embed", "track"]):
        for attr in ATRIBUTOS_SRC:
            if tag.get(attr):
                candidatos.add(tag[attr])
        for attr in ("srcset", "data-srcset", "data-lazy-srcset"):
            if tag.get(attr):
                mejor = mejor_de_srcset(tag[attr])
                if mejor:
                    candidatos.add(mejor)

    for a in soup.find_all("a", href=True):
        candidatos.add(a["href"])

    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in {"og:image", "og:video", "og:video:url", "og:audio", "twitter:image"}:
            if meta.get("content"):
                candidatos.add(meta["content"])

    # url(...) dentro de estilos inline / <style>
    for m in re.finditer(r"url\(['\"]?([^'\")]+)['\"]?\)", html):
        candidatos.add(m.group(1))

    resultado: set[str] = set()
    for c in candidatos:
        c = c.strip()
        if not c or c.startswith(("data:", "javascript:", "#", "mailto:")):
            continue
        absoluta = urljoin(base_url, c).split("#")[0]
        if not absoluta.startswith(("http://", "https://")):
            continue
        if extension(absoluta) in MEDIA_EXT:
            if originales:
                absoluta = WP_SIZE.sub("", absoluta)
            resultado.add(absoluta)
    if con_texto:
        resultado |= extraer_urls_texto(html, base_url, originales)
    return resultado


RE_URL_TEXTO = re.compile(r"(?:https?:)?//[^" + _FIN + r"]+", re.I)
RE_RUTA_TEXTO = re.compile(r"""["'](/[^\s"'<>\\()]+)["']""")


def extraer_enlaces_sitio(html: str, base_url: str, sitio: str, mismo_dominio: bool = True,
                          originales: bool = False):
    """Busca las páginas de detalle a visitar: todas las URLs que contengan `sitio`,
    ya sea en <a href>, en onclick/JavaScript o en cualquier parte del texto, tengan o no <img>.
    Devuelve ({url: {miniaturas}}, total_de_<a>, muestras_de_enlaces)."""
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base_url).netloc.lower().removeprefix("www.")
    patron = re.sub(r"^https?://", "", (sitio or "").strip().lower())
    con_dominio = bool(patron) and not patron.startswith("/")
    items: dict[str, set[str]] = {}
    muestras: list[str] = []
    anchors = soup.find_all("a", href=True)

    def aceptar(crudo: str):
        crudo = crudo.strip().rstrip(".,;:")
        if not crudo or crudo.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            return None
        u = urljoin(base_url, crudo).split("#")[0]
        if not u.startswith(("http://", "https://")) or extension(u) in MEDIA_EXT:
            return None
        if u.rstrip("/") == base_url.rstrip("/"):
            return None
        netloc = urlparse(u).netloc.lower().removeprefix("www.")
        if mismo_dominio and not con_dominio and host and netloc != host:
            return None
        return u

    def coincide(u: str) -> bool:
        return (patron in re.sub(r"^https?://", "", u.lower())) if patron else True

    for a in anchors:
        u = aceptar(a["href"])
        if not u:
            continue
        if len(muestras) < 8 and u not in muestras:
            muestras.append(u)
        thumbs = extraer_media(str(a), base_url, originales)
        if patron:
            if not coincide(u):
                continue
        elif not thumbs:
            continue
        items.setdefault(u, set()).update(thumbs)

    if patron:  # enlaces fuera de <a>: onclick, JSON, location='...', etc.
        t = normalizar_texto(html)
        for cand in [m.group(0) for m in RE_URL_TEXTO.finditer(t)] + [m.group(1) for m in RE_RUTA_TEXTO.finditer(t)]:
            u = aceptar(cand)
            if u and coincide(u):
                items.setdefault(u, set())
    return items, len(anchors), muestras


def _num(v) -> int:
    m = re.match(r"\d+", str(v or ""))
    return int(m.group()) if m else 0


def puntuar_detalle(html: str, url: str, originales: bool, excluir) -> dict[str, float]:
    """Asigna una puntuación a cada archivo media de la página de detalle para
    adivinar cuál es la imagen principal (la grande)."""
    soup = BeautifulSoup(html, "html.parser")
    puntos: dict[str, float] = {}

    def sumar(crudo: str, pts: float, sin_ext: bool = False) -> None:
        u = urljoin(url, crudo.strip()).split("#")[0]
        if not u.startswith(("http://", "https://")):
            return
        if originales:
            u = WP_SIZE.sub("", u)
        ext = extension(u)
        if ext not in MEDIA_EXT and not (sin_ext and ext not in EXT_NO_MEDIA):
            return  # (sin_ext: <img src="/img/123"> sin extensión también cuenta)
        if u in excluir:
            return
        puntos[u] = puntos.get(u, 0) + pts

    for el in soup.find_all(["img", "source", "video", "a"]):
        base = 0.0
        pista = " ".join(el.get("class", [])) + " " + (el.get("id") or "")
        if PISTAS_BUENAS.search(pista):
            base += 3
        if PISTAS_MALAS.search(pista):
            base -= 6
        if el.find_parent(["main", "article"]):
            base += 2
        if el.find_parent(["header", "footer", "nav", "aside"]):
            base -= 4
        ancho = _num(el.get("width"))
        base += min(ancho * _num(el.get("height")) / 50000, 6)
        if 0 < ancho < 120:
            base -= 3

        for attr in ATRIBUTOS_SRC + (("href",) if el.name == "a" else ()):
            v = el.get(attr)
            if v:
                extra = 4 if attr in ATRIBUTOS_GRANDES else (2 if attr == "href" else 0)
                sumar(v, base + extra, sin_ext=el.name in ("img", "source", "video") and attr != "href")
        for attr in ("srcset", "data-srcset"):
            if el.get(attr):
                mejor = mejor_de_srcset(el[attr])
                if mejor:
                    sumar(mejor, base + 1, sin_ext=el.name in ("img", "source"))

    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in {"og:image", "og:image:url", "og:video", "og:video:url", "twitter:image"}:
            if meta.get("content"):
                sumar(meta["content"], 4)

    for u in sorted(extraer_urls_texto(html, url, originales)):
        sumar(u, 0)

    for u in list(puntos):
        if PISTAS_MALAS.search(urlparse(u).path):
            puntos[u] -= 6
        if TRACKERS.search(u):
            puntos[u] -= 10
        if WP_SIZE.search(u):
            puntos[u] -= 3
    return puntos


def media_de_detalle(sesion, url, referer, originales, excluir,
                     selector="", todas=False, depurar=False) -> set[str]:
    """Abre la página de detalle (/s/...) y devuelve su imagen principal.
    - selector: selector CSS que señala la imagen exacta (ej. "img#foto-grande").
    - sin selector: elige la imagen con mayor puntuación (grande, en <main>, atributos
      data-full, og:image, sin sufijo -300x200...), ignorando lo que ya estaba en la
      página madre (logos, menús, miniaturas).
    - todas=True: devuelve todo lo nuevo en vez de solo la principal."""
    r = sesion.get(url, timeout=30, headers={"Referer": referer})
    r.raise_for_status()
    if "html" not in r.headers.get("Content-Type", "html"):
        return set()
    html = html_de(r)

    if selector:
        soup = BeautifulSoup(html, "html.parser")
        encontrados: set[str] = set()
        for el in soup.select(selector):
            encontrados |= extraer_media(str(el), url, originales)
            for sub in [el] + el.find_all(["img", "source", "video"]):
                if sub.name in ("img", "source", "video"):
                    for attr in ATRIBUTOS_SRC:
                        v = sub.get(attr)
                        if v:
                            u = urljoin(url, v.strip()).split("#")[0]
                            if u.startswith(("http://", "https://")) and extension(u) not in EXT_NO_MEDIA:
                                encontrados.add(WP_SIZE.sub("", u) if originales else u)
        if depurar:
            print(f"   [detalle] {url}\n      selector '{selector}': {sorted(encontrados) or 'SIN COINCIDENCIAS'}")
        return encontrados

    puntos = puntuar_detalle(html, url, originales, excluir)
    if depurar:
        print(f"   [detalle] {url}")
        for u, pts in sorted(puntos.items(), key=lambda kv: -kv[1])[:3]:
            print(f"      {pts:5.1f}  {u}")
        if not puntos:
            print("      (sin candidatos)")
    if not puntos:
        return set()
    if todas:
        return set(puntos)
    return {max(puntos, key=puntos.get)}


def nombre_archivo(url: str, usados: set[str]) -> str:
    nombre = slug(unquote(Path(urlparse(url).path).name), 150)
    if nombre in usados:
        stem, suf = Path(nombre).stem, Path(nombre).suffix
        nombre = f"{stem}_{hashlib.md5(url.encode()).hexdigest()[:6]}{suf}"
    usados.add(nombre)
    return nombre


def descargar(sesion: requests.Session, url: str, destino: Path, referer: str) -> str:
    """Descarga en streaming. Devuelve 'ok', 'omitido' o 'error: ...'.
    Si la URL no trae extensión (ej. /img/123), se deduce del Content-Type."""
    if destino.suffix:
        if destino.exists() and destino.stat().st_size > 0:
            return "omitido"
    elif any(f.stat().st_size > 0 for f in destino.parent.glob(destino.name + ".*")):
        return "omitido"
    tmp = None
    try:
        ref = REFERER_FIJO or referer
        headers = {"Referer": ref} if ref else {}
        with sesion.get(url, stream=True, timeout=30, headers=headers) as r:
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ct.startswith("text/html"):
                return "error: el servidor devolvió una página HTML en vez del archivo (¿protección anti-descarga o login?)"
            if not destino.suffix:
                ext = CT_EXT.get(ct)
                if not ext:
                    return f"error: no parece un archivo de media (Content-Type: {ct or 'desconocido'})"
                destino = destino.with_name(destino.name + ext)
                if destino.exists() and destino.stat().st_size > 0:
                    return "omitido"
            tmp = destino.with_suffix(destino.suffix + ".part")
            with open(tmp, "wb") as f:
                for bloque in r.iter_content(CHUNK):
                    if bloque:
                        f.write(bloque)
        tmp.replace(destino)
        return "ok"
    except Exception as e:  # noqa: BLE001
        if tmp is not None and tmp.exists():
            tmp.unlink(missing_ok=True)
        return f"error: {describir_error(e)}"


def usar_ytdlp(url: str, carpeta: Path) -> None:
    exe = shutil.which("yt-dlp")
    if not exe:
        print("   (yt-dlp no está instalado; omito paso de video embebido)")
        return
    subprocess.run(
        [exe, "-q", "--no-warnings", "--no-playlist",
         "-o", str(carpeta / "%(title).80s [%(id)s].%(ext)s"), url],
        check=False,
    )


def url_con_pagina(url: str, param: str, n: int) -> str:
    """Devuelve la URL con ?param=n (reemplaza el valor si ya existía)."""
    p = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != param]
    q.append((param, str(n)))
    return urlunparse(p._replace(query=urlencode(q)))


def pagina_inicial(url: str, param: str) -> int | None:
    for k, v in parse_qsl(urlparse(url).query):
        if k == param and v.isdigit():
            return int(v)
    return None


def seguir_grid(sesion, html, url, medios, vistos_enlaces, args, log_errores, referers) -> int:
    """Visita las páginas que coinciden con SITIO/--sitio y cambia cada miniatura por la
    imagen grande de la página. Modifica `medios` y `referers` en sitio.
    Devuelve cuántos enlaces nuevos se siguieron."""
    items, n_a, muestras = extraer_enlaces_sitio(html, url, args.sitio, not args.otros_dominios, args.originales)
    pendientes = {h: t for h, t in items.items() if h not in vistos_enlaces}
    pendientes = dict(list(pendientes.items())[: args.max_enlaces])
    filtro = args.sitio or "(enlaces con miniatura)"
    print(f"   enlaces: {n_a} <a> en la página | {len(items)} coinciden con '{filtro}' "
          f"| {len(pendientes)} nuevos por seguir")
    if not items:
        print("   Ninguno coincide con el filtro (variable SITIO o --sitio). Ejemplos de enlaces que sí hay en la página:")
        for m in muestras:
            print("      ", m)
        if not muestras:
            print("       (la página no trae enlaces <a>: puede cargarse con JavaScript; usa --fuente con el código fuente)")
    if not pendientes:
        return 0
    if args.prueba:
        for h in list(pendientes)[:3]:
            print(f"      visitará: {h}")

    base_madre = frozenset(medios)
    hallados = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(media_de_detalle, sesion, h, url, args.originales, base_madre,
                        args.selector_detalle, args.todas_detalle,
                        args.prueba and i < 5): h
            for i, h in enumerate(pendientes)
        }
        for fut in as_completed(futs):
            h = futs[fut]
            vistos_enlaces.add(h)
            try:
                nuevos = fut.result()
            except Exception as e:  # noqa: BLE001
                log_errores.append(f"{h}\tGRID\t{e}")
                print(f"      no pude abrir {h}: {describir_error(e)}")
                continue
            if nuevos:
                hallados += 1
                medios -= pendientes[h]  # cambia la miniatura por la imagen completa
                medios |= nuevos
                for u in nuevos:
                    referers[u] = h  # la imagen se pide con su página /s/... como Referer
            else:
                log_errores.append(f"{h}\tGRID\tno se encontró imagen grande")
    print(f"   imágenes completas halladas en {hallados} de {len(pendientes)} enlaces")
    return len(pendientes)


def descargar_lote(sesion, medios, carpeta, usados, workers, referer, log_errores, referers=None):
    referers = referers or {}
    ok = omit = err = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tareas = {}
        for m in sorted(medios):
            ref = referers.get(m, referer)
            nombre = nombre_archivo(m, usados)
            if m in referers:  # viene de una página /s/NUMERO: el número ordena y evita choques
                pref = slug(Path(urlparse(ref).path.rstrip("/")).name, 40)
                if pref and pref not in nombre:
                    nombre = f"{pref}_{nombre}"
            tareas[pool.submit(descargar, sesion, m, carpeta / nombre, ref)] = (m, ref)
        for fut in as_completed(tareas):
            res = fut.result()
            if res == "ok":
                ok += 1
            elif res == "omitido":
                omit += 1
            else:
                err += 1
                m, ref = tareas[fut]
                log_errores.append(f"{m}\t{ref}\t{res}")
                if err <= 5:
                    print(f"      {res}  <- {m}")
    if err > 5:
        print(f"      ... y {err - 5} errores más (ver errores.txt)")
    return ok, omit, err


def procesar_url(sesion, entrada, base_salida, args, log_errores):
    print(f"\n==> {entrada}")
    originales, usar_titulo = args.originales, not args.carpeta_url

    local = not entrada.startswith(("http://", "https://")) and Path(entrada).expanduser().is_file()
    html = None
    if local:
        html = Path(entrada).expanduser().read_text(encoding="utf-8", errors="ignore")
        url = args.base_url or inferir_base(html)
        print(f"   código fuente local | URL base: "
              f"{url or '(no detectada; para rutas relativas usa --base-url https://tusitio.com)'}")
    else:
        url = entrada

    directo = bool(url) and extension(url) in MEDIA_EXT
    paginar = args.paginar and bool(url)
    inicio = pagina_inicial(url, args.param_pagina) if paginar else None
    n = inicio or 1

    if html is None:
        try:
            r = sesion.get(url, timeout=30)
            r.raise_for_status()
            html = html_de(r)
        except Exception as e:  # noqa: BLE001
            print(f"   ERROR al abrir la página: {describir_error(e)}")
            print("   (si el sitio bloquea scripts o carga con JavaScript: abre la página en tu navegador,"
                  " copia el código fuente a un .html y usa --fuente archivo.html)")
            log_errores.append(f"{url}\tPAGINA\t{e}")
            return

    carpeta = carpeta_para_pagina(base_salida, url or Path(entrada).stem, html, usar_titulo)
    carpeta.mkdir(parents=True, exist_ok=True)
    print(f"   carpeta: {carpeta.name}")
    if not directo:
        (carpeta / "pagina.html").write_text(html, encoding="utf-8", errors="ignore")

    usados: set[str] = set()
    vistos_medios: set[str] = set()
    vistos_enlaces: set[str] = set()
    referers: dict[str, str] = {}
    lista_prueba: list[str] = []
    tot_ok = tot_omit = tot_err = 0
    pagina_url = url
    primera = True
    paginas_hechas = 0

    while True:
        if not primera:
            pagina_url = url_con_pagina(url, args.param_pagina, n)
            try:
                r = sesion.get(pagina_url, timeout=30)
                r.raise_for_status()
                html = html_de(r)
            except Exception as e:  # noqa: BLE001
                print(f"   [pág {n}] fin de paginación ({e})")
                break

        enlaces_nuevos = 0
        if directo:
            medios = {url}
        else:
            print(f"   [pág {n}] {pagina_url}")
            medios = extraer_media(html, pagina_url, originales)
            if not args.sin_grid:
                enlaces_nuevos = seguir_grid(sesion, html, pagina_url, medios,
                                             vistos_enlaces, args, log_errores, referers)

        nuevos_medios = medios - vistos_medios
        extra = ""
        if primera and not directo:
            solo_texto = len(extraer_urls_texto(html, pagina_url, originales) - extraer_media_estructura(html, pagina_url, originales))
            extra = f" (HTML {len(html) // 1024} KB; {solo_texto} hallados solo en texto crudo)"
        print(f"   [pág {n}] {len(medios)} archivos media, {len(nuevos_medios)} nuevos{extra}")
        paginas_hechas += 1

        if not nuevos_medios and enlaces_nuevos == 0:
            if primera and not medios:
                print("   AVISO: 0 archivos media. Causas probables: la página los carga con JavaScript o el "
                      "sitio bloquea scripts.\n   Abre la página en tu navegador, copia el código fuente "
                      "(F12 > clic derecho en <html> > Copy > Copy outerHTML) a un .html y usa --fuente archivo.html")
            if not primera:
                print(f"   [pág {n}] sin contenido nuevo: fin de paginación")
            break
        vistos_medios |= medios

        if args.prueba:
            lista_prueba.extend(sorted(nuevos_medios))
        else:
            ok, omit, err = descargar_lote(sesion, nuevos_medios, carpeta, usados,
                                           args.workers, pagina_url, log_errores, referers)
            tot_ok, tot_omit, tot_err = tot_ok + ok, tot_omit + omit, tot_err + err
            print(f"   descargados: {ok} | ya existían: {omit} | errores: {err}")

        if directo or not paginar:
            break
        if paginas_hechas >= args.max_paginas:
            print(f"   límite de {args.max_paginas} páginas alcanzado (--max-paginas)")
            break
        n += 1
        primera = False

    if args.prueba:
        (carpeta / "lista_prueba.txt").write_text("\n".join(lista_prueba), encoding="utf-8")
        print(f"   PRUEBA: {len(lista_prueba)} archivos se descargarían -> {carpeta / 'lista_prueba.txt'}")
    elif paginar:
        print(f"   TOTAL {paginas_hechas} páginas | descargados: {tot_ok} | "
              f"ya existían: {tot_omit} | errores: {tot_err}")

    if args.ytdlp and not args.prueba:
        usar_ytdlp(url, carpeta)


def leer_urls(ruta: Path) -> list[str]:
    urls = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            urls.append(linea)
    return list(dict.fromkeys(urls))  # quita duplicados conservando orden


def main():
    ap = argparse.ArgumentParser(description="Respalda los archivos media de una lista de URLs.")
    ap.add_argument("-i", "--input", default=None, help="archivo con URLs (default: urls.txt)")
    ap.add_argument("-o", "--output", default="respaldo", help="carpeta de salida (default: respaldo)")
    ap.add_argument("-w", "--workers", type=int, default=4, help="descargas simultáneas por URL (default: 4)")
    ap.add_argument("--originales", action="store_true", help="WordPress: quita sufijo -300x200 para bajar el original")
    ap.add_argument("--ytdlp", action="store_true", help="usa yt-dlp para videos embebidos (YouTube, Vimeo...)")
    ap.add_argument("--carpeta-url", action="store_true", help="nombrar carpetas con la URL en vez del h1/title")
    ap.add_argument("--sin-grid", action="store_true", help="no seguir los enlaces de las miniaturas del grid")
    ap.add_argument("--max-enlaces", type=int, default=300, help="máximo de enlaces de grid por página (default: 300)")
    ap.add_argument("--sitio", "--patron-grid", dest="sitio", default=SITIO,
                    help='filtro de las URLs a visitar (default: la variable SITIO del script, "%s"). '
                         'Ej.: --sitio "midominio.com/s/"' % SITIO)
    ap.add_argument("--paginar", action="store_true", help="recorrer la paginación ?p=1, ?p=2, ... hasta que no haya contenido nuevo")
    ap.add_argument("--param-pagina", default="p", help="nombre del parámetro de paginación (default: p)")
    ap.add_argument("--max-paginas", type=int, default=200, help="tope de páginas por URL (default: 200)")
    ap.add_argument("--prueba", action="store_true", help="no descarga: solo lista lo que descargaría (lista_prueba.txt)")
    ap.add_argument("--selector-detalle", default="",
                    help='selector CSS de la imagen grande en la página /s/... (ej. "img#foto" o "div.visor img")')
    ap.add_argument("--todas-detalle", action="store_true",
                    help="en la página /s/... bajar todo el media nuevo, no solo la imagen principal")
    ap.add_argument("--fuente", nargs="+", metavar="ARCHIVO_O_CARPETA",
                    help="código fuente guardado (.html) o carpeta con varios; como pegarlo en JDownloader")
    ap.add_argument("--base-url", default="", help="URL original del código fuente (para resolver rutas relativas)")
    ap.add_argument("--cookie", default="", help='cabecera Cookie, ej. "sesion=abc; edad=1" (sitios con login/verificación)')
    ap.add_argument("--cabeceras-archivo", default="",
                    help='archivo con las cabeceras de tu navegador (pega ahí un "Copy as cURL (bash)" de una imagen)')
    ap.add_argument("--header", action="append", metavar='"Nombre: valor"', help="cabecera extra (se puede repetir)")
    ap.add_argument("--referer", default="", help="forzar este Referer en todas las descargas, ej. https://tusitio.com/")
    ap.add_argument("--user-agent", default="", help="User-Agent a usar (por defecto uno de Chrome)")
    ap.add_argument("--diagnostico", metavar="URL_IMAGEN", default="",
                    help="prueba descargar UNA imagen con distintas cabeceras y explica qué protección hay")
    ap.add_argument("--pagina", default="", help="con --diagnostico: la página /s/... donde aparece esa imagen")
    ap.add_argument("--otros-dominios", action="store_true", help="seguir también enlaces de grid hacia otros dominios")
    args = ap.parse_args()

    sesion = crear_sesion()
    configurar_sesion(sesion, args)
    if args.diagnostico:
        diagnostico(sesion, args.diagnostico, args.pagina)
        return

    entradas: list[str] = []
    if args.input or not args.fuente:
        ruta = Path(args.input or "urls.txt")
        if not ruta.exists():
            sys.exit(f"No encuentro {ruta}. Crea el archivo con una URL por línea (o usa --fuente archivo.html).")
        entradas += leer_urls(ruta)
    for f in args.fuente or []:
        pth = Path(f).expanduser()
        if pth.is_dir():
            entradas += sorted(str(x) for x in pth.iterdir() if x.suffix.lower() in {".html", ".htm", ".txt"})
        elif pth.is_file():
            entradas.append(str(pth))
        else:
            print(f"(no existe {f}, se omite)")
    urls = list(dict.fromkeys(entradas))
    salida = Path(args.output)
    salida.mkdir(parents=True, exist_ok=True)
    print(f"{len(urls)} URLs -> {salida.resolve()}")

    errores: list[str] = []
    for i, u in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}]", end="")
        procesar_url(sesion, u, salida, args, errores)

    if errores:
        (salida / "errores.txt").write_text("\n".join(errores), encoding="utf-8")
        print(f"\nTerminado con {len(errores)} errores -> {salida / 'errores.txt'}")
    else:
        print("\nTerminado sin errores.")


if __name__ == "__main__":
    main()
