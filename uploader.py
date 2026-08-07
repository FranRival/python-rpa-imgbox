import os
import sys
import time
import traceback
from pathlib import Path

# 🔥 EVITA BLOQUEOS DE CMD / .BAT
sys.stdin = open(os.devnull)

# =========================
# LOG A ARCHIVO (útil cuando corre desatendido vía .bat)
# =========================
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploader_log.txt")

def log(msg):
    print(msg)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from openpyxl import Workbook, load_workbook


# =========================
# CONFIGURACIÓN
# =========================

IMGBOX_URL = "https://imgbox.com/upload"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}


# =========================
# UTILIDADES
# =========================

def pausar_y_salir(codigo=1):
    """
    Si se ejecuta interactivamente (doble clic / terminal), espera ENTER
    para que la ventana no se cierre sola.
    Si se ejecuta desde el .bat orquestador (stdin = nul), NO intenta leer
    input (eso lanzaría EOFError) y simplemente termina con el código dado.
    """
    try:
        interactivo = sys.stdin.isatty()
    except Exception:
        interactivo = False

    if interactivo:
        input("\nPresiona ENTER para salir...")

    sys.exit(codigo)


def obtener_subcarpetas(root):
    return [
        os.path.join(root, d)
        for d in sorted(os.listdir(root))
        if os.path.isdir(os.path.join(root, d))
    ]


# =========================
# EXCEL (1 ARCHIVO POR BATCH)
# =========================

def get_excel_path(batch_root):
    batch_name = os.path.basename(batch_root.rstrip("\\/"))
    return os.path.join(batch_root, f"{batch_name}.xlsx")


def ensure_excel(path):
    if not os.path.exists(path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        wb.save(path)
    return load_workbook(path)


def find_or_create_column(ws, header):
    max_col = ws.max_column
    for col in range(1, max_col + 1):
        if (ws.cell(row=1, column=col).value or "").strip() == header:
            return col

    new_col = max_col + 1
    ws.cell(row=1, column=new_col, value=header)
    return new_col


def write_html_to_excel(excel_path, folder_name, html):
    wb = ensure_excel(excel_path)
    ws = wb["Sheet1"]

    col = find_or_create_column(ws, folder_name)
    ws.cell(row=2, column=col, value=html)

    wb.save(excel_path)
    print(f"💾 Excel actualizado → {excel_path} | Columna: {folder_name}")


# =========================
# SELENIUM
# =========================

# Ruta al chromedriver descargado manualmente desde
# https://googlechromelabs.github.io/chrome-for-testing/
# (evita que Selenium Manager se cuelgue intentando auto-detectar la versión)
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"


def init_driver():
    """
    Abre Chrome usando el chromedriver descargado manualmente (ruta fija),
    evitando por completo la auto-detección de Selenium Manager / webdriver_manager,
    que se estaba colgando indefinidamente con Chrome 151.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if not os.path.exists(CHROMEDRIVER_PATH):
        raise FileNotFoundError(
            f"No se encontró chromedriver en: {CHROMEDRIVER_PATH}\n"
            f"Verifica que lo descargaste y descomprimiste ahí."
        )

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ Chrome iniciado con chromedriver manual")
    driver.set_page_load_timeout(60)
    return driver


def seleccionar_adult_content(driver):
    time.sleep(2)
    driver.execute_script("""
        try {
            var s = document.getElementById('dropdown-content-type');
            if (s) {
                s.value = '2';
                s.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (typeof $ !== 'undefined' && $.fn.selectpicker) {
                $('#dropdown-content-type').selectpicker('val','2');
                $('#dropdown-content-type').selectpicker('refresh');
            }
        } catch(e) {}
    """)
    time.sleep(1)


# =========================
# ESPERA REAL (SIN TIMEOUT)
# =========================

def extract_fullsize_html(driver):
    try:
        for a in driver.find_elements(By.TAG_NAME, "textarea"):
            val = (a.get_attribute("value") or "").strip()
            lower = val.lower()
            if val and "<img" in val and "imgbox.com" in lower and "thumb" not in lower:
                return val
    except:
        pass
    return ""


def esperar_html_final(driver):
    print("⌛ Esperando HTML FINAL...")
    while True:
        html = extract_fullsize_html(driver)
        if html:
            print("✅ HTML detectado")
            return html
        time.sleep(3)


# =========================
# PROCESO DE SUBIDA
# =========================

def subir_carpeta(driver, excel_path, folder):
    archivos = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if Path(f).suffix.lower() in ALLOWED_EXT
    ]

    if not archivos:
        print(f"⚠️ Carpeta vacía: {folder}")
        return

    nombre_carpeta = os.path.basename(folder)

    print("\n📁 SUBCARPETA ACTUAL (RUTA COMPLETA):")
    print(folder)
    print(f"📦 Archivos: {len(archivos)}")

    driver.get(IMGBOX_URL)
    time.sleep(3)

    seleccionar_adult_content(driver)

    wait = WebDriverWait(driver, 30)
    input_file = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
    )

    input_file.send_keys("\n".join(archivos))
    time.sleep(2)

    start_btn = wait.until(
        EC.element_to_be_clickable((By.ID, "fake-submit-button"))
    )
    driver.execute_script("arguments[0].click();", start_btn)

    html = esperar_html_final(driver)
    write_html_to_excel(excel_path, nombre_carpeta, html)


# =========================
# MAIN
# =========================

def main():
    # --- Validar argumento ---
    if len(sys.argv) < 2:
        print("❌ No se recibió ruta del batch")
        print("Uso: python uploader_corregido.py \"C:\\ruta\\al\\batch\"")
        pausar_y_salir(1)

    batch_root = sys.argv[1]

    if not os.path.isdir(batch_root):
        print(f"❌ La ruta no existe o no es una carpeta: {batch_root}")
        pausar_y_salir(1)

    print("\n🚀 INICIANDO UPLOADER")
    print("📂 RUTA COMPLETA DEL BATCH:")
    print(batch_root)

    excel_path = get_excel_path(batch_root)
    print(f"📊 Excel del batch: {excel_path}")

    carpetas = obtener_subcarpetas(batch_root)
    print(f"📁 Total carpetas: {len(carpetas)}")

    if not carpetas:
        print("⚠️ No se encontraron subcarpetas en el batch. Nada que hacer.")
        pausar_y_salir(0)

    # --- Abrir Chrome con manejo de errores explícito ---
    try:
        driver = init_driver()
    except Exception:
        log("\n❌ ERROR CRÍTICO: no se pudo abrir Chrome")
        log(traceback.format_exc())
        pausar_y_salir(1)
        return  # nunca llega aquí, pero por claridad

    try:
        for idx, carpeta in enumerate(carpetas, 1):
            print(f"\n➡️ {idx}/{len(carpetas)}")
            subir_carpeta(driver, excel_path, carpeta)

        print("\n🏁 BATCH COMPLETADO")

    except Exception:
        print("\n❌ ERROR CRÍTICO DURANTE LA EJECUCIÓN")
        traceback.print_exc()

    finally:
        time.sleep(5)
        driver.quit()
        print("✅ Proceso terminado")

    pausar_y_salir(0)


if __name__ == "__main__":
    main()