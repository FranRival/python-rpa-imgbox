#!/usr/bin/env python3
"""
Extrae de un código fuente (HTML, JS, etc.) solo las URLs que comienzan
con uno o varios prefijos dados. Todo lo demás se descarta.

Uso:
  python extraer_urls.py codigo.html -p https://ejemplo.com/media/
  python extraer_urls.py codigo.html -p https://a.com/ https://b.com/ -o urls.txt
  python extraer_urls.py            (modo interactivo: pregunta los datos)
"""
import argparse
import re
import sys
from pathlib import Path

# Captura cualquier URL http/https hasta un carácter que no pueda formar parte de ella
URL_REGEX = re.compile(r"""https?://[^\s"'<>\\)\]}]+""", re.IGNORECASE)


def extraer_urls(texto: str, prefijos: list[str]) -> list[str]:
    """Devuelve las URLs únicas (en orden de aparición) que empiezan con algún prefijo."""
    vistas = set()
    resultado = []
    for url in URL_REGEX.findall(texto):
        url = url.rstrip(".,;")  # limpia puntuación final
        if any(url.startswith(p) for p in prefijos) and url not in vistas:
            vistas.add(url)
            resultado.append(url)
    return resultado


def leer_archivo(ruta: Path) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return ruta.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("No se pudo leer el archivo con una codificación conocida.")


def main():
    parser = argparse.ArgumentParser(description="Extrae URLs por prefijo de un código fuente.")
    parser.add_argument("archivo", nargs="?", help="Archivo con el código fuente")
    parser.add_argument("-p", "--prefijo", nargs="+", help="Uno o más prefijos de URL")
    parser.add_argument("-o", "--salida", help="Archivo de salida (por defecto: urls_extraidas.txt)")
    args = parser.parse_args()

    interactivo = not args.archivo or not args.prefijo
    archivo = args.archivo or input("Ruta del archivo de código fuente: ").strip().strip('"')
    prefijos = args.prefijo or [
        p.strip() for p in input("Prefijo(s) de URL (separados por espacio): ").split() if p.strip()
    ]

    ruta = Path(archivo)
    if not ruta.is_file():
        sys.exit(f"Error: no existe el archivo '{archivo}'")
    if not prefijos:
        sys.exit("Error: debes indicar al menos un prefijo.")

    urls = extraer_urls(leer_archivo(ruta), prefijos)

    salida = Path(args.salida or "urls_extraidas.txt")
    salida.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")

    print(f"{len(urls)} URL(s) encontradas -> {salida.resolve()}")
    if interactivo:
        input("Pulsa Enter para salir...")


if __name__ == "__main__":
    main()