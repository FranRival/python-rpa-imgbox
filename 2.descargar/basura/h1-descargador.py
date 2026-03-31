import os
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_DIR = r"C:\Users\dell\Downloads\marzo\aaa"
LINKS_FILE = "links.txt"
TIMEOUT = 30
DELAY = 1.0

os.makedirs(BASE_DIR, exist_ok=True)

def limpiar_nombre(texto):
    texto = texto.strip()
    texto = re.sub(r'[\\/:*?"<>|]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto[:180]

def obtener_nombre(html):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1:
        return limpiar_nombre(h1.get_text())

    if soup.title:
        return limpiar_nombre(soup.title.string)

    return None

# cargar links
with open(LINKS_FILE, "r", encoding="utf-8") as f:
    urls = [u.strip() for u in f if u.strip()]

session = requests.Session()

for i, url in enumerate(urls, 1):
    print(f"[{i}] {url}")

    try:
        r = session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"❌ Error: {e}")
        continue

    nombre = obtener_nombre(html) or f"pagina_{i}"
    carpeta = os.path.join(BASE_DIR, nombre)
    os.makedirs(carpeta, exist_ok=True)

    with open(os.path.join(carpeta, "source.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Guardado en: {nombre}")

    time.sleep(DELAY)

print("🏁 Terminado")