import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# ==========================================
# CONFIGURACIÓN
# ==========================================

ARCHIVO_HTML = "sitio_completo.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ==========================================


def limpiar_nombre(nombre):
    nombre = re.sub(r'[<>:"/\\|?*]', '', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre[:120]


def obtener_nombre(soup):

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return "Sitio"


def obtener_url_base(html):

    # Busca la primera URL registrada en los comentarios
    m = re.search(r'URL:\s*(https?://[^\s]+)', html)

    if m:
        return m.group(1)

    return None


def descargar_imagen(url, carpeta):

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)

        if r.status_code != 200:
            print("No se pudo descargar:", url)
            return

        nombre = os.path.basename(urlparse(url).path)

        if nombre == "":
            nombre = "imagen"

        ruta = os.path.join(carpeta, nombre)

        # Evita duplicados
        if os.path.exists(ruta):
            return

        with open(ruta, "wb") as f:
            f.write(r.content)

        print("Descargada:", nombre)

    except Exception as e:
        print("Error:", url)
        print(e)


def main():

    with open(ARCHIVO_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    nombre = limpiar_nombre(obtener_nombre(soup))

    carpeta = nombre

    os.makedirs(carpeta_img, exist_ok=True)

    base = obtener_url_base(html)

    if base is None:
        print("No se encontró la URL base.")
        return

    imagenes = set()

    # etiquetas <img>
    for img in soup.find_all("img"):

        src = img.get("src")

        if not src:
            continue

        imagenes.add(urljoin(base, src))

    # descarga
    print(f"\nSe encontraron {len(imagenes)} imágenes.\n")

    for img in sorted(imagenes):
        descargar_imagen(img, carpeta_img)

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()