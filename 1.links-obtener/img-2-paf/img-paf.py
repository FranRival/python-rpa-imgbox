import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def obtener_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return None


def encontrar_siguiente(soup, url_actual):
    """
    Busca la siguiente página mediante diferentes estrategias.
    """

    # 1. rel="next"
    link = soup.find("link", rel="next")
    if link and link.get("href"):
        return urljoin(url_actual, link["href"])

    a = soup.find("a", rel="next")
    if a and a.get("href"):
        return urljoin(url_actual, a["href"])

    # 2. Buscar enlaces que contengan /page/
    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/page/" in href:
            return urljoin(url_actual, href)

    # 3. Buscar ?page=
    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "page=" in href:
            return urljoin(url_actual, href)

    return None


def descargar_paginacion(url_inicial, archivo_salida):
    visitadas = set()
    url = url_inicial

    with open(archivo_salida, "w", encoding="utf-8") as f:

        while url and url not in visitadas:

            print("Descargando:", url)

            visitadas.add(url)

            html = obtener_html(url)

            if html is None:
                break

            f.write("=" * 80 + "\n")
            f.write(f"URL: {url}\n")
            f.write("=" * 80 + "\n\n")
            f.write(html)
            f.write("\n\n\n")

            soup = BeautifulSoup(html, "html.parser")

            siguiente = encontrar_siguiente(soup, url)

            if siguiente in visitadas:
                break

            url = siguiente

            time.sleep(1)

    print(f"\nTerminado. Se guardó en {archivo_salida}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("url", help="URL inicial")
    parser.add_argument(
        "-o",
        "--output",
        default="codigo_fuente.txt",
        help="Archivo de salida"
    )

    args = parser.parse_args()

    descargar_paginacion(args.url, args.output)