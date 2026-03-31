import requests
from bs4 import BeautifulSoup
import os
import re
import time
from urllib.parse import urlparse

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = r"C:\Users\dell\Downloads\marzo\aaa\2"
LINKS_FILE = "links.txt"
TIMEOUT = 30
DELAY = 1.2   # 🔴 importante para no bloquear tan rápido

os.makedirs(BASE_DIR, exist_ok=True)

# =========================
# UTILIDADES
# =========================
def limpiar_nombre(texto):
    texto = texto.replace(".html", "")
    texto = texto.replace("-", " ")

    # Caracteres inválidos en Windows
    texto = re.sub(r'[\\/:*?"<>|]', '', texto)

    # Espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto[:180] if texto else None


def nombre_desde_url(url):
    path = urlparse(url).path
    nombre = os.path.basename(path)

    if not nombre:
        return None

    return limpiar_nombre(nombre)

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

    nombre_carpeta = nombre_desde_url(url)

    if not nombre_carpeta:
        print("⚠️ No se pudo obtener nombre desde la URL")
        continue

    ruta_carpeta = os.path.join(BASE_DIR, nombre_carpeta)
    os.makedirs(ruta_carpeta, exist_ok=True)

    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        # Guardar HTML SIEMPRE (aunque esté bloqueado)
        ruta_html = os.path.join(ruta_carpeta, "source.html")
        with open(ruta_html, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"✅ Carpeta y source.html creados: {ruta_carpeta}")

    except Exception as e:
        print(f"❌ Error descargando HTML: {e}")

    time.sleep(DELAY)

print("\n🏁 Proceso finalizado.")
