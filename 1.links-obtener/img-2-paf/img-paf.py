import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# =====================================================
# CONFIGURACIÓN
# =====================================================

URL = "https://----"
ARCHIVO_SALIDA = "sitio_completo.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def obtener_html(url):
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=20)
        respuesta.raise_for_status()
        return respuesta.text
    except Exception as e:
        print(f"Error descargando {url}")
        print(e)
        return None


def encontrar_siguiente(soup, url_actual):
    """Busca la siguiente página."""

    # rel="next"
    link = soup.find("link", rel="next")
    if link and link.get("href"):
        return urljoin(url_actual, link["href"])

    a = soup.find("a", rel="next")
    if a and a.get("href"):
        return urljoin(url_actual, a["href"])

    # /page/
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if "/page/" in href:
            return urljoin(url_actual, href)

    # ?page=
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if "page=" in href:
            return urljoin(url_actual, href)

    return None


def descargar_paginacion():

    visitadas = set()
    url = URL

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as archivo:

        while url and url not in visitadas:

            print(f"Descargando: {url}")

            visitadas.add(url)

            html = obtener_html(url)

            if html is None:
                break

            archivo.write("\n")
            archivo.write("<!-- ====================================================== -->\n")
            archivo.write(f"<!-- URL: {url} -->\n")
            archivo.write("<!-- ====================================================== -->\n\n")

            archivo.write(html)
            archivo.write("\n\n")

            soup = BeautifulSoup(html, "html.parser")

            siguiente = encontrar_siguiente(soup, url)

            if siguiente in visitadas:
                break

            url = siguiente

            time.sleep(1)

    print("\nProceso terminado.")
    print(f"Archivo generado: {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    descargar_paginacion()