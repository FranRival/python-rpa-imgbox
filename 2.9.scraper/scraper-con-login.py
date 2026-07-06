import os
import re
import time
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog, scrolledtext

TIMEOUT = 30
DELAY = 1.0

# URLs del sitio
LOGIN_PAGE_URL = "https://www.poringa.net/login?redirect=%2F"
LOGIN_URL = "https://www.poringa.net/registro/login-submit.php"

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
# LOGIN
# =========================
def hacer_login(session, usuario, password):
    """
    Envía el POST de login y devuelve True/False según si parece haber
    funcionado. Ajusta la validación si el sitio cambia su comportamiento.
    """
    headers_comunes = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
    }

    # Paso 1: cargar la página de login primero para obtener las cookies
    # iniciales de sesión (el sitio las genera al visitar /login).
    try:
        r0 = session.get(LOGIN_PAGE_URL, headers=headers_comunes, timeout=TIMEOUT)
        r0.raise_for_status()
    except Exception as e:
        log(f"❌ Error al cargar la página de login: {e}")
        return False

    # Paso 2: enviar el POST de login como petición AJAX (XHR),
    # igual que hace el navegador real.
    payload = {
        "nick": usuario,
        "pass": password,
        "connect": "",
        "redirect": "/",
    }

    headers = {
        **headers_comunes,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.poringa.net",
        "Referer": LOGIN_PAGE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        r = session.post(LOGIN_URL, data=payload, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        log(f"❌ Error al hacer login: {e}")
        return False

    # Verificación básica: revisamos si el sitio nos sigue mandando
    # a una página de login o si ya tenemos cookies de sesión activas.
    texto = r.text.lower()
    cookies_sesion = session.cookies.get_dict()

    if not cookies_sesion:
        log("⚠️ No se recibieron cookies de sesión. El login pudo haber fallado.")
        return False

    if "login" in r.url.lower() and "usuario o contraseña" in texto:
        log("❌ Login incorrecto: usuario o contraseña inválidos.")
        return False

    log(f"✅ Login realizado. Cookies obtenidas: {list(cookies_sesion.keys())}")
    return True


# =========================
# PROCESAMIENTO
# =========================
def ejecutar():
    carpeta_txt = entry_txt.get()
    carpeta_salida = entry_out.get()
    usuario = entry_user.get().strip()
    password = entry_pass.get().strip()

    if not os.path.isdir(carpeta_txt):
        log("❌ Carpeta TXT inválida")
        return
    if not os.path.isdir(carpeta_salida):
        os.makedirs(carpeta_salida, exist_ok=True)

    if not usuario or not password:
        log("❌ Debes ingresar usuario y contraseña")
        return

    archivos = [f for f in os.listdir(carpeta_txt) if f.endswith(".txt")]

    session = requests.Session()

    log("🔐 Iniciando sesión...")
    if not hacer_login(session, usuario, password):
        log("🛑 Abortando: no se pudo iniciar sesión. Revisa usuario/contraseña.")
        return

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

            # Aviso si detectamos que nos redirigió al login
            # (posible pérdida de sesión a mitad de proceso)
            if "login" in r.url.lower():
                log("⚠️ Posible sesión expirada o redirección a login detectada")

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
root.title("Scraper HTML por lotes (con login)")
root.geometry("700x600")

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

# Usuario / contraseña
tk.Label(frame, text="Usuario:").grid(row=4, column=0, sticky="w", pady=(10, 0))
entry_user = tk.Entry(frame, width=40)
entry_user.grid(row=5, column=0, sticky="w")

tk.Label(frame, text="Contraseña:").grid(row=6, column=0, sticky="w", pady=(10, 0))
entry_pass = tk.Entry(frame, width=40, show="*")
entry_pass.grid(row=7, column=0, sticky="w")

# Botón ejecutar
tk.Button(root, text="▶ Ejecutar", command=ejecutar, height=2, bg="green", fg="white").pack(pady=10)

# Logs
log_box = scrolledtext.ScrolledText(root, width=85, height=20)
log_box.pack(pady=10)

root.mainloop()