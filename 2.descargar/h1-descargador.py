import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = r"C:\Users\dell\Downloads\marzo\aaa"
LINKS_FILE = "links.txt"

TIMEOUT = 30
DELAY = 1.2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

os.makedirs(BASE_DIR, exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)

# =========================
# UTILIDADES
# =========================
def limpiar_nombre(texto):
    texto = texto.strip()
    texto = re.sub(r'[\\/:*?"<>|]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto[:180]

def obtener_nombre_desde_html(html):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return limpiar_nombre(h1.get_text())

    if soup.title and soup.title.string:
        return limpiar_nombre(soup.title.string)

    return None

def normalizar_url(src, base_url):
    if not src:
        return None

    src = src.strip()

    if src.startswith("data:"):
        return None

    return urljoin(base_url, src)

def nombre_archivo_desde_url(url, index):
    nombre = os.path.basename(urlparse(url).path)
    if not nombre or len(nombre) < 3:
        nombre = f"img_{index}.jpg"
    return nombre.split("?")[0]

def descargar_imagen(url, destino):
    try:
        with session.get(url, timeout=TIMEOUT, stream=True) as r:
            r.raise_for_status()
            with open(destino, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
    except:
        pass

# =========================
# CARGAR LINKS
# =========================
with open(LINKS_FILE, "r", encoding="utf-8") as f:
    urls = [u.strip() for u in f if u.strip()]

print(f"🔗 URLs: {len(urls)}")

# =========================
# PROCESAMIENTO
# =========================
for i, url in enumerate(urls, 1):
    print(f"\n[{i}/{len(urls)}] {url}")

    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        html = response.text

    except Exception as e:
        print(f"❌ Error descargando HTML: {e}")
        continue

    # =========================
    # NOMBRE DE CARPETA (H1 o TITLE)
    # =========================
    nombre = obtener_nombre_desde_html(html)

    if not nombre:
        nombre = f"pagina_{i}"

    ruta_carpeta = os.path.join(BASE_DIR, nombre)
    os.makedirs(ruta_carpeta, exist_ok=True)

    # =========================
    # GUARDAR HTML
    # =========================
    ruta_html = os.path.join(ruta_carpeta, "source.html")
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📁 Carpeta creada: {nombre}")

    # =========================
    # EXTRAER Y DESCARGAR IMÁGENES
    # =========================
    soup = BeautifulSoup(html, "html.parser")
    imagenes = set()

    for img in soup.find_all("img"):
        src = (
            img.get("src") or
            img.get("data-src") or
            img.get("data-original") or
            img.get("data-lazy")
        )

        url_img = normalizar_url(src, url)
        if url_img:
            imagenes.add(url_img)

    print(f"🖼️ Imágenes: {len(imagenes)}")

    for j, img_url in enumerate(imagenes, 1):
        try:
            nombre_img = nombre_archivo_desde_url(img_url, j)
            destino = os.path.join(ruta_carpeta, nombre_img)

            if os.path.exists(destino):
                continue

            descargar_imagen(img_url, destino)
            print(f"   ✅ {nombre_img}")

            time.sleep(0.3)

        except Exception as e:
            print(f"   ❌ {img_url}")

    time.sleep(DELAY)

print("\n🏁 Proceso terminado.")