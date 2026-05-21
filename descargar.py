import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = r"C:\Users\dell\Downloads\marzo\aaa"
DELAY = 0.4
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ✅ NUEVO: Ruta del TXT en el escritorio
ESCRITORIO = os.path.join(os.path.expanduser("~"), "Desktop")
TXT_VIDEOS = os.path.join(ESCRITORIO, "videos_sendvid.txt")

# Dominios de video a detectar
VIDEO_DOMINIOS = ("sendvid.com", "sendvideo.com")

session = requests.Session()
session.headers.update(BASE_HEADERS)

# =========================
# UTILIDADES
# =========================
def construir_referer_desde_imagen(img_url):
    parsed = urlparse(img_url)
    return f"{parsed.scheme}://{parsed.netloc}/"

def descargar_imagen(url, destino, reintentos=2):
    headers = BASE_HEADERS.copy()
    headers["Referer"] = construir_referer_desde_imagen(url)
    for intento in range(1, reintentos + 1):
        try:
            with session.get(
                url,
                headers=headers,
                timeout=(10, 20),
                stream=True
            ) as r:
                r.raise_for_status()
                with open(destino, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if not chunk:
                            break
                        f.write(chunk)
                r.close()
                return
        except Exception as e:
            if intento == reintentos:
                raise e
            time.sleep(1.5)

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
    return None

# ✅ NUEVO: Función para guardar URL de video en el TXT
def registrar_url_video(url, carpeta_origen):
    with open(TXT_VIDEOS, "a", encoding="utf-8") as f:
        f.write(f"{url}    # {carpeta_origen}\n")

# =========================
# PROCESAMIENTO RECURSIVO
# =========================
for root, dirs, files in os.walk(BASE_DIR):
    if "source.html" not in files:
        continue
    html_path = os.path.join(root, "source.html")
    print(f"\n📂 Procesando: {root}")
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"❌ Error leyendo source.html -> {e}")
        continue

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
        if not url or url.startswith("data:"):
            continue
        imagenes.add(url)

    print(f"🖼️ Imágenes detectadas: {len(imagenes)}")

    for i, img_url in enumerate(imagenes, 1):
        # ✅ NUEVO: Detectar URLs de video antes de intentar descargar
        dominio = urlparse(img_url).netloc.lower()
        if any(dominio.endswith(v) for v in VIDEO_DOMINIOS):
            registrar_url_video(img_url, root)
            print(f"   🎬 Video detectado y registrado: {img_url}")
            continue  # No intenta descargar como imagen

        try:
            nombre = nombre_archivo_desde_url(img_url, i)
            destino = os.path.join(root, nombre)
            if os.path.exists(destino):
                continue
            descargar_imagen(img_url, destino)
            print(f"   ✅ {nombre}")
            time.sleep(DELAY)
        except Exception as e:
            print(f"   ❌ Error {img_url} -> {e}")

print("\n🏁 Proceso terminado.")