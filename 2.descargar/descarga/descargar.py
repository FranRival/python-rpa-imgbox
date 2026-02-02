import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = r"C:\Users\dell\Downloads\marzo\aaa\a1"
TIMEOUT = 40
DELAY = 0.4

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session()
session.headers.update(BASE_HEADERS)

# =========================
# UTILIDADES
# =========================
def construir_referer_desde_imagen(img_url):
    """
    Crea un referer válido desde el dominio de la imagen.
    Ej: https://cdn.site.com/img.jpg -> https://cdn.site.com/
    """
    parsed = urlparse(img_url)
    return f"{parsed.scheme}://{parsed.netloc}/"

def descargar_imagen(url, destino):
    referer = construir_referer_desde_imagen(url)

    headers = BASE_HEADERS.copy()
    headers["Referer"] = referer

    with session.get(url, headers=headers, timeout=TIMEOUT, stream=True) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

def nombre_archivo_desde_url(url, index):
    nombre = os.path.basename(urlparse(url).path)
    if not nombre or len(nombre) < 3:
        nombre = f"img_{index}.jpg"
    return nombre.split("?")[0]

def normalizar_url(src):
    src = src.strip()

    if src.startswith("//"):
        return "https:" + src

    if src.startswith("http://") or src.startswith("https://"):
        return src

    # Si viene una ruta rara, se ignora
    return None

# =========================
# PROCESAMIENTO
# =========================
for carpeta in os.listdir(BASE_DIR):
    ruta_carpeta = os.path.join(BASE_DIR, carpeta)

    if not os.path.isdir(ruta_carpeta):
        continue

    html_path = os.path.join(ruta_carpeta, "source.html")
    if not os.path.exists(html_path):
        print(f"⚠️ No existe source.html en {carpeta}")
        continue

    print(f"\n📂 Procesando: {carpeta}")

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    imagenes = set()

    for img in soup.find_all("img"):
        src = (
            img.get("src") or
            img.get("data-src") or
            img.get("data-original") or
            img.get("data-lazy")
        )

        if not src:
            continue

        url = normalizar_url(src)
        if not url:
            continue

        if url.startswith("data:"):
            continue

        imagenes.add(url)

    print(f"🖼️ Detectadas: {len(imagenes)} imágenes")

    for i, img_url in enumerate(imagenes, 1):
        try:
            nombre = nombre_archivo_desde_url(img_url, i)
            destino = os.path.join(ruta_carpeta, nombre)

            if os.path.exists(destino):
                continue

            descargar_imagen(img_url, destino)
            print(f"   ✅ {nombre}")

            time.sleep(DELAY)

        except Exception as e:
            print(f"   ❌ Error  {img_url} -> {e}")

print("\n🏁 Proceso terminado.")
