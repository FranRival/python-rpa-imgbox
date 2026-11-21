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
    python respaldar_media.py --paginar --patron-grid /s/
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
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

CHUNK = 256 * 1024  # 256 KB: se escribe a disco por partes, RAM mínima
WP_SIZE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[a-zA-Z0-9]+$)")


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


def extraer_media(html: str, base_url: str, originales: bool) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidatos: set[str] = set()

    atributos_src = (
        "src", "data-src", "data-lazy-src", "data-original", "poster", "data-full-url",
        "data-full", "data-large", "data-large_image", "data-zoom-image",
        "data-orig-file", "data-large-file", "data-image", "data-bg",
    )
    for tag in soup.find_all(["img", "video", "audio", "source", "embed", "track"]):
        for attr in atributos_src:
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
        if extension(absoluta) in MEDIA_EXT:
            if originales:
                absoluta = WP_SIZE.sub("", absoluta)
            resultado.add(absoluta)
    return resultado


def extraer_grid(html: str, base_url: str, mismo_dominio: bool = True, patron: str = ""):
    """Encuentra miniaturas que enlazan a OTRA página (típico grid/galería).
    Si `patron` no está vacío (ej. "/s/"), solo se conservan los enlaces cuya ruta lo contenga.
    Devuelve ({url_destino: {urls_de_sus_miniaturas}}, total_de_enlaces_con_miniatura)."""
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base_url).netloc
    items: dict[str, set[str]] = {}
    total = 0
    for a in soup.find_all("a", href=True):
        img = a.find("img")
        if not img:
            continue
        href = urljoin(base_url, a["href"].strip()).split("#")[0]
        if not href.startswith(("http://", "https://")):
            continue
        if extension(href) in MEDIA_EXT:  # ya lo cubre extraer_media
            continue
        if href.rstrip("/") == base_url.rstrip("/"):
            continue
        if mismo_dominio and urlparse(href).netloc != host:
            continue
        total += 1
        if patron and patron not in urlparse(href).path:
            continue
        items.setdefault(href, set()).update(extraer_media(str(img), base_url, False))
    return items, total


def media_de_detalle(sesion, url, referer, originales, excluir) -> set[str]:
    """Abre la página de detalle de un item del grid y saca su media principal.
    Toma el media que NO estaba ya en la página madre (así se descartan logos, menús
    y miniaturas repetidas); si no queda nada, usa og:image/og:video como respaldo."""
    r = sesion.get(url, timeout=30, headers={"Referer": referer})
    r.raise_for_status()
    if "html" not in r.headers.get("Content-Type", "html"):
        return set()
    html = html_de(r)

    soup = BeautifulSoup(html, "html.parser")
    og: set[str] = set()
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in {"og:image", "og:image:url", "og:video", "og:video:url", "twitter:image"}:
            if meta.get("content"):
                absoluta = urljoin(url, meta["content"].strip()).split("#")[0]
                if extension(absoluta) in MEDIA_EXT:
                    og.add(WP_SIZE.sub("", absoluta) if originales else absoluta)

    todos = extraer_media(html, url, originales)
    nuevos = todos - excluir
    return nuevos or og


def nombre_archivo(url: str, usados: set[str]) -> str:
    nombre = slug(unquote(Path(urlparse(url).path).name), 150)
    if nombre in usados:
        stem, suf = Path(nombre).stem, Path(nombre).suffix
        nombre = f"{stem}_{hashlib.md5(url.encode()).hexdigest()[:6]}{suf}"
    usados.add(nombre)
    return nombre


def descargar(sesion: requests.Session, url: str, destino: Path, referer: str) -> str:
    """Descarga en streaming. Devuelve 'ok', 'omitido' o 'error: ...'."""
    if destino.exists() and destino.stat().st_size > 0:
        return "omitido"
    tmp = destino.with_suffix(destino.suffix + ".part")
    try:
        with sesion.get(url, stream=True, timeout=30, headers={"Referer": referer}) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for bloque in r.iter_content(CHUNK):
                    if bloque:
                        f.write(bloque)
        tmp.replace(destino)
        return "ok"
    except Exception as e:  # noqa: BLE001
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return f"error: {e}"


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


def seguir_grid(sesion, html, url, medios, vistos_enlaces, args, log_errores) -> int:
    """Entra a los enlaces del grid (que coincidan con --patron-grid) y cambia cada
    miniatura por la imagen completa. Modifica `medios` en sitio.
    Devuelve cuántos enlaces nuevos se siguieron."""
    items, total = extraer_grid(html, url, not args.otros_dominios, args.patron_grid)
    pendientes = {h: t for h, t in items.items() if h not in vistos_enlaces}
    pendientes = dict(list(pendientes.items())[: args.max_enlaces])
    patron = args.patron_grid or "(todos)"
    print(f"   grid: {total} enlaces con miniatura | {len(items)} coinciden con {patron} "
          f"| {len(pendientes)} nuevos por seguir")
    if not pendientes:
        return 0

    base_madre = frozenset(medios)
    hallados = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(media_de_detalle, sesion, h, url, args.originales, base_madre): h
            for h in pendientes
        }
        for fut in as_completed(futs):
            h = futs[fut]
            vistos_enlaces.add(h)
            try:
                nuevos = fut.result()
            except Exception as e:  # noqa: BLE001
                log_errores.append(f"{h}\tGRID\t{e}")
                continue
            if nuevos:
                hallados += 1
                medios -= pendientes[h]  # cambia la miniatura por la imagen completa
                medios |= nuevos
    print(f"   imágenes completas halladas en {hallados} de {len(pendientes)} enlaces")
    return len(pendientes)


def descargar_lote(sesion, medios, carpeta, usados, workers, referer, log_errores):
    ok = omit = err = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tareas = {}
        for m in sorted(medios):
            destino = carpeta / nombre_archivo(m, usados)
            tareas[pool.submit(descargar, sesion, m, destino, referer)] = m
        for fut in as_completed(tareas):
            res = fut.result()
            if res == "ok":
                ok += 1
            elif res == "omitido":
                omit += 1
            else:
                err += 1
                log_errores.append(f"{tareas[fut]}\t{referer}\t{res}")
    return ok, omit, err


def procesar_url(sesion, url, base_salida, args, log_errores):
    print(f"\n==> {url}")
    originales, usar_titulo = args.originales, not args.carpeta_url
    directo = extension(url) in MEDIA_EXT
    inicio = pagina_inicial(url, args.param_pagina) if args.paginar else None
    n = inicio or 1

    try:
        r = sesion.get(url, timeout=30)
        r.raise_for_status()
        html = html_de(r)
    except Exception as e:  # noqa: BLE001
        print(f"   ERROR al abrir la página: {e}")
        log_errores.append(f"{url}\tPAGINA\t{e}")
        return

    carpeta = carpeta_para_pagina(base_salida, url, html, usar_titulo)
    carpeta.mkdir(parents=True, exist_ok=True)
    print(f"   carpeta: {carpeta.name}")
    if not directo:
        (carpeta / "pagina.html").write_text(html, encoding="utf-8", errors="ignore")

    usados: set[str] = set()
    vistos_medios: set[str] = set()
    vistos_enlaces: set[str] = set()
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
                                             vistos_enlaces, args, log_errores)

        nuevos_medios = medios - vistos_medios
        print(f"   [pág {n}] {len(medios)} archivos media, {len(nuevos_medios)} nuevos")
        paginas_hechas += 1

        if not nuevos_medios and enlaces_nuevos == 0:
            if not primera:
                print(f"   [pág {n}] sin contenido nuevo: fin de paginación")
            break
        vistos_medios |= medios

        if args.prueba:
            lista_prueba.extend(sorted(nuevos_medios))
        else:
            ok, omit, err = descargar_lote(sesion, nuevos_medios, carpeta, usados,
                                           args.workers, pagina_url, log_errores)
            tot_ok, tot_omit, tot_err = tot_ok + ok, tot_omit + omit, tot_err + err
            print(f"   descargados: {ok} | ya existían: {omit} | errores: {err}")

        if directo or not args.paginar:
            break
        if paginas_hechas >= args.max_paginas:
            print(f"   límite de {args.max_paginas} páginas alcanzado (--max-paginas)")
            break
        n += 1
        primera = False

    if args.prueba:
        (carpeta / "lista_prueba.txt").write_text("\n".join(lista_prueba), encoding="utf-8")
        print(f"   PRUEBA: {len(lista_prueba)} archivos se descargarían -> {carpeta / 'lista_prueba.txt'}")
    elif args.paginar:
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
    ap.add_argument("-i", "--input", default="urls.txt", help="archivo con URLs (default: urls.txt)")
    ap.add_argument("-o", "--output", default="respaldo", help="carpeta de salida (default: respaldo)")
    ap.add_argument("-w", "--workers", type=int, default=4, help="descargas simultáneas por URL (default: 4)")
    ap.add_argument("--originales", action="store_true", help="WordPress: quita sufijo -300x200 para bajar el original")
    ap.add_argument("--ytdlp", action="store_true", help="usa yt-dlp para videos embebidos (YouTube, Vimeo...)")
    ap.add_argument("--carpeta-url", action="store_true", help="nombrar carpetas con la URL en vez del h1/title")
    ap.add_argument("--sin-grid", action="store_true", help="no seguir los enlaces de las miniaturas del grid")
    ap.add_argument("--max-enlaces", type=int, default=300, help="máximo de enlaces de grid por página (default: 300)")
    ap.add_argument("--patron-grid", default="/s/",
                    help='solo seguir enlaces del grid cuya ruta contenga esto (default: "/s/"; usa "" para seguir todos)')
    ap.add_argument("--paginar", action="store_true", help="recorrer la paginación ?p=1, ?p=2, ... hasta que no haya contenido nuevo")
    ap.add_argument("--param-pagina", default="p", help="nombre del parámetro de paginación (default: p)")
    ap.add_argument("--max-paginas", type=int, default=200, help="tope de páginas por URL (default: 200)")
    ap.add_argument("--prueba", action="store_true", help="no descarga: solo lista lo que descargaría (lista_prueba.txt)")
    ap.add_argument("--otros-dominios", action="store_true", help="seguir también enlaces de grid hacia otros dominios")
    args = ap.parse_args()

    ruta = Path(args.input)
    if not ruta.exists():
        sys.exit(f"No encuentro {ruta}. Crea el archivo con una URL por línea.")

    urls = leer_urls(ruta)
    salida = Path(args.output)
    salida.mkdir(parents=True, exist_ok=True)
    print(f"{len(urls)} URLs -> {salida.resolve()}")

    sesion = crear_sesion()
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
