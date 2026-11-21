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
from urllib.parse import urljoin, urlparse, unquote

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


def slug(texto: str, maximo: int = 80) -> str:
    texto = re.sub(r"[^\w.\-]+", "_", texto, flags=re.UNICODE).strip("_")
    return texto[:maximo] or "pagina"


def carpeta_para_url(base: Path, url: str) -> Path:
    p = urlparse(url)
    nombre = slug(p.netloc + p.path)
    if p.query:
        nombre += "_" + hashlib.md5(p.query.encode()).hexdigest()[:6]
    return base / nombre


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

    atributos_src = ("src", "data-src", "data-lazy-src", "data-original", "poster", "data-full-url")
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


def procesar_url(sesion, url, base_salida, workers, originales, ytdlp, log_errores):
    print(f"\n==> {url}")
    carpeta = carpeta_para_url(base_salida, url)
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        r = sesion.get(url, timeout=30)
        r.raise_for_status()
        html = r.text
    except Exception as e:  # noqa: BLE001
        print(f"   ERROR al abrir la página: {e}")
        log_errores.append(f"{url}\tPAGINA\t{e}")
        return

    # Si la URL apunta directo a un archivo media, bájalo y listo
    if extension(url) in MEDIA_EXT:
        medios = {url}
    else:
        medios = extraer_media(html, url, originales)
        (carpeta / "pagina.html").write_text(html, encoding="utf-8", errors="ignore")

    print(f"   {len(medios)} archivos media encontrados")

    usados: set[str] = set()
    tareas = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for m in sorted(medios):
            destino = carpeta / nombre_archivo(m, usados)
            tareas[pool.submit(descargar, sesion, m, destino, url)] = m
        ok = omit = err = 0
        for fut in as_completed(tareas):
            res = fut.result()
            if res == "ok":
                ok += 1
            elif res == "omitido":
                omit += 1
            else:
                err += 1
                log_errores.append(f"{tareas[fut]}\t{url}\t{res}")
    print(f"   descargados: {ok} | ya existían: {omit} | errores: {err}")

    if ytdlp:
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
        procesar_url(sesion, u, salida, args.workers, args.originales, args.ytdlp, errores)

    if errores:
        (salida / "errores.txt").write_text("\n".join(errores), encoding="utf-8")
        print(f"\nTerminado con {len(errores)} errores -> {salida / 'errores.txt'}")
    else:
        print("\nTerminado sin errores.")


if __name__ == "__main__":
    main()
