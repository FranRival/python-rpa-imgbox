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

# Ruta del TXT en el escritorio (funciona con cualquier usuario de Windows)
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
                timeout=(10, 20),  # connect, read
                stream=True
            ) as r:
                r.raise_for_status()
                with open(destino, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if not chunk:
                            break
                        f.write(chunk)
                r.close()
                return  # éxito
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

def es_dominio_video(url):
    """Devuelve True si la URL pertenece a un dominio de video conocido."""
    try:
        dominio = urlparse(url).netloc.lower()
        return any(dominio.endswith(v) for v in VIDEO_DOMINIOS)
    except Exception:
        return False

def registrar_url_video(url, carpeta_origen):
    """Escribe la URL de video en el TXT del escritorio (modo append)."""
    try:
        with open(TXT_VIDEOS, "a", encoding="utf-8") as f:
            f.write(f"{url}    # {carpeta_origen}\n")
    except Exception as e:
        print(f"   ⚠️  No se pudo escribir en {TXT_VIDEOS} -> {e}")

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

    # -------------------------
    # 1. Recolectar imágenes
    # -------------------------
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

    # -------------------------
    # 2. Detectar iframes de video (sendvid / sendvideo)
    # -------------------------
    videos_encontrados = 0
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "").strip()
        if not src:
            continue
        url = normalizar_url(src)
        if not url:
            continue
        if es_dominio_video(url):
            registrar_url_video(url, root)
            print(f"   🎬 iframe de video registrado: {url}")
            videos_encontrados += 1

    if videos_encontrados == 0:
        print(f"   (sin iframes de video en esta carpeta)")

    # -------------------------
    # 3. Descargar imágenes
    # -------------------------
    print(f"🖼️  Imágenes detectadas: {len(imagenes)}")

    for i, img_url in enumerate(imagenes, 1):
        # Por si acaso alguna imagen también apunta a un dominio de video, la omitimos
        if es_dominio_video(img_url):
            registrar_url_video(img_url, root)
            print(f"   🎬 URL de video en <img> registrada: {img_url}")
            continue

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
print(f"📄 URLs de video guardadas en: {TXT_VIDEOS}")