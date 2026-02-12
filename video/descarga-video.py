import requests
from bs4 import BeautifulSoup
import os
import re
import time
from urllib.parse import urljoin

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = r"C:\Users\dell\Downloads\marzo\aaa\134"
LINKS_FILE = "links.txt"
TIMEOUT = 60
DELAY = 2

os.makedirs(BASE_DIR, exist_ok=True)

# =========================
# UTILIDADES
# =========================
def limpiar_nombre(texto):
    if not texto:
        return None

    texto = texto.strip()

    # Eliminar saltos de línea
    texto = re.sub(r'[\r\n]+', ' ', texto)

    # Quitar caracteres inválidos en Windows
    texto = re.sub(r'[\\/:*?"<>|]', '', texto)

    # Quitar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()

    # Limitar longitud
    return texto[:140]


def nombre_unico(ruta_base):
    """
    Si el archivo existe, agrega (1), (2), etc.
    """
    if not os.path.exists(ruta_base):
        return ruta_base

    base, ext = os.path.splitext(ruta_base)
    contador = 1

    while True:
        nueva_ruta = f"{base} ({contador}){ext}"
        if not os.path.exists(nueva_ruta):
            return nueva_ruta
        contador += 1


def extraer_mp4(soup, base_url):
    # Buscar en etiquetas <video> y <source>
    for tag in soup.find_all(["video", "source"]):
        src = tag.get("src")
        if src and ".mp4" in src:
            return urljoin(base_url, src)

    # Buscar cualquier .mp4 en el HTML
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and ".mp4" in href:
            return urljoin(base_url, href)

    return None


# =========================
# CARGAR LINKS
# =========================
with open(LINKS_FILE, "r", encoding="utf-8") as f:
    urls = [u.strip() for u in f if u.strip()]

print(f"🔗 URLs detectadas: {len(urls)}")
print(f"📁 Carpeta destino: {BASE_DIR}")

# =========================
# SESIÓN HTTP
# =========================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

# =========================
# PROCESAMIENTO
# =========================
for i, url in enumerate(urls, 1):
    print(f"\n[{i}/{len(urls)}] Procesando:")
    print(url)

    try:
        # 1️⃣ Descargar HTML
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 2️⃣ Extraer H1
        h1_tag = soup.find("h1")
        titulo = limpiar_nombre(h1_tag.get_text()) if h1_tag else None

        if not titulo:
            print("⚠️ No se encontró H1. Usando nombre alternativo.")
            titulo = f"video_{i}"

        # 3️⃣ Buscar mp4 en HTML
        mp4_url = extraer_mp4(soup, url)

        if not mp4_url:
            print("❌ No se encontró ningún archivo .mp4 en la página.")
            continue

        print(f"🎬 MP4 encontrado: {mp4_url}")

        # 4️⃣ Descargar MP4 en stream
        video_response = session.get(mp4_url, timeout=TIMEOUT, stream=True)
        video_response.raise_for_status()

        content_type = video_response.headers.get("Content-Type", "")
        if "video" not in content_type:
            print(f"⚠️ Advertencia Content-Type inesperado: {content_type}")

        ruta_video = os.path.join(BASE_DIR, f"{titulo}.mp4")
        ruta_video = nombre_unico(ruta_video)

        with open(ruta_video, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print(f"✅ Descargado correctamente: {ruta_video}")

    except Exception as e:
        print(f"❌ Error: {e}")

    time.sleep(DELAY)

print("\n🏁 Proceso finalizado.")
