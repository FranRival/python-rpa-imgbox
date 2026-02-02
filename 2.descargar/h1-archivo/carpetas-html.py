import requests
from bs4 import BeautifulSoup
import os
import re
import time

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = r"C:\Users\dell\Downloads\pruebas"
LINKS_FILE = "links.txt"
SIN_H1_FILE = "sin_h1_urls.txt"
TIMEOUT = 30
DELAY = 1   # segundos entre requests

os.makedirs(BASE_DIR, exist_ok=True)

# =========================
# UTILIDADES
# =========================
def limpiar_nombre(texto):
    if not texto:
        return None

    texto = texto.strip()

    # 1️⃣ Eliminar sufijo fijo del sitio (Poringa)
    texto = re.sub(r'\s*-\s*Poringa!?\s*$', '', texto, flags=re.IGNORECASE)

    # 2️⃣ Eliminar caracteres inválidos en Windows
    texto = re.sub(r'[\\/:*?"<>|]', '', texto)

    # 3️⃣ Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto).strip()

    # 4️⃣ Validación fuerte
    if not texto or texto.lower() == "poringa":
        return None

    return texto[:180]

# =========================
# CARGAR LINKS
# =========================
with open(LINKS_FILE, "r", encoding="utf-8") as f:
    urls = [u.strip() for u in f if u.strip()]

print(f"🔗 URLs detectadas: {len(urls)}")
print(f"📁 Carpeta destino: {BASE_DIR}")

# Limpiar archivo de URLs descartadas
open(SIN_H1_FILE, "w", encoding="utf-8").close()

# =========================
# PROCESAMIENTO
# =========================
for i, url in enumerate(urls, 1):
    print(f"\n[{i}/{len(urls)}] Procesando:")
    print(url)

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        title = soup.find("title")

        nombre_base = None
        origen = None

        if h1 and h1.get_text(strip=True):
            nombre_base = h1.get_text()
            origen = "H1"
        elif title and title.get_text(strip=True):
            nombre_base = title.get_text()
            origen = "TITLE"

        nombre_carpeta = limpiar_nombre(nombre_base)

        if not nombre_carpeta:
            print("⚠️ H1/TITLE no usable. URL enviada a sin_h1_urls.txt")
            with open(SIN_H1_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            continue

        ruta_carpeta = os.path.join(BASE_DIR, nombre_carpeta)
        os.makedirs(ruta_carpeta, exist_ok=True)

        # Guardar código fuente
        ruta_html = os.path.join(ruta_carpeta, "source.html")
        with open(ruta_html, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅ Carpeta creada ({origen}): {ruta_carpeta}")

        time.sleep(DELAY)

    except Exception as e:
        print(f"❌ Error en {url}: {e}")

print("\n🏁 Proceso finalizado.")
