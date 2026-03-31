import os
import re
import time
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog, scrolledtext

TIMEOUT = 30
DELAY = 1.0

# =========================
# UTILIDADES
# =========================
def limpiar_nombre(texto):
    texto = texto.strip()
    texto = re.sub(r'[\\/:*?"<>|]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto[:180]

def obtener_nombre(html):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return limpiar_nombre(h1.get_text())

    if soup.title and soup.title.string:
        return limpiar_nombre(soup.title.string)

    return None

def log(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)
    root.update()

# =========================
# PROCESAMIENTO
# =========================
def ejecutar():
    carpeta_txt = entry_txt.get()
    carpeta_salida = entry_out.get()

    if not os.path.isdir(carpeta_txt):
        log("❌ Carpeta TXT inválida")
        return

    if not os.path.isdir(carpeta_salida):
        os.makedirs(carpeta_salida, exist_ok=True)

    archivos = [f for f in os.listdir(carpeta_txt) if f.endswith(".txt")]

    session = requests.Session()

    for archivo in archivos:
        ruta_txt = os.path.join(carpeta_txt, archivo)
        nombre_base = os.path.splitext(archivo)[0]

        carpeta_madre = os.path.join(carpeta_salida, nombre_base)
        os.makedirs(carpeta_madre, exist_ok=True)

        log(f"\n📂 Procesando archivo: {archivo}")

        try:
            with open(ruta_txt, "r", encoding="utf-8") as f:
                urls = [u.strip() for u in f if u.strip()]
        except:
            log("❌ Error leyendo archivo")
            continue

        for i, url in enumerate(urls, 1):
            log(f"[{i}/{len(urls)}] {url}")

            try:
                r = session.get(url, timeout=TIMEOUT)
                r.raise_for_status()
                html = r.text
            except Exception as e:
                log(f"❌ Error: {e}")
                continue

            nombre = obtener_nombre(html) or f"pagina_{i}"
            carpeta_final = os.path.join(carpeta_madre, nombre)
            os.makedirs(carpeta_final, exist_ok=True)

            ruta_html = os.path.join(carpeta_final, "source.html")
            with open(ruta_html, "w", encoding="utf-8") as f:
                f.write(html)

            log(f"✅ Guardado en: {nombre}")

            time.sleep(DELAY)

    log("\n🏁 TERMINADO")

# =========================
# UI
# =========================
root = tk.Tk()
root.title("Scraper HTML por lotes")
root.geometry("700x500")

frame = tk.Frame(root)
frame.pack(pady=10)

# Input TXT
tk.Label(frame, text="Carpeta de archivos TXT:").grid(row=0, column=0, sticky="w")
entry_txt = tk.Entry(frame, width=60)
entry_txt.grid(row=1, column=0)
tk.Button(frame, text="Seleccionar", command=lambda: entry_txt.insert(0, filedialog.askdirectory())).grid(row=1, column=1)

# Input Output
tk.Label(frame, text="Carpeta destino:").grid(row=2, column=0, sticky="w")
entry_out = tk.Entry(frame, width=60)
entry_out.grid(row=3, column=0)
tk.Button(frame, text="Seleccionar", command=lambda: entry_out.insert(0, filedialog.askdirectory())).grid(row=3, column=1)

# Botón ejecutar
tk.Button(root, text="▶ Ejecutar", command=ejecutar, height=2, bg="green", fg="white").pack(pady=10)

# Logs
log_box = scrolledtext.ScrolledText(root, width=85, height=20)
log_box.pack(pady=10)

root.mainloop()