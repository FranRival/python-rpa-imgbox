import os
import sys
import time
import traceback
from pathlib import Path

# Guardar si el stdin ORIGINAL era interactivo, ANTES de redirigirlo.
# (open(os.devnull) en Windows abre NUL, que reporta isatty() == True,
#  por eso hay que medirlo antes de reemplazar sys.stdin)
try:
    ES_INTERACTIVO = sys.stdin.isatty()
except Exception:
    ES_INTERACTIVO = False

# Evita bloqueos de CMD / .BAT
sys.stdin = open(os.devnull)

# Evita caracteres raros (Γ¥î) en la consola de Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# =========================
# LOG A ARCHIVO (útil cuando corre desatendido vía .bat)
# =========================
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploader_log.txt")


def log(msg):
    try:
        print(msg)
    except Exception:
        pass
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

# Ruta al chromedriver descargado manualmente desde
# https://googlechromelabs.github.io/chrome-for-testing/
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"

# Dejar vacío ("") para usar el Chrome instalado normalmente.
# Si quieres usar Chrome for Testing, pon aquí la ruta completa a su chrome.exe.
CHROME_BINARY_PATH = ""


# =========================
# UTILIDADES
# =========================

def pausar_y_salir(codigo=1):
    """
    Si el script se lanzó de forma interactiva (doble clic / terminal),
    espera ENTER para que la ventana no se cierre sola.
    Si lo lanzó el .bat orquestador, termina sin pedir input.
    """
    if ES_INTERACTIVO:
        try:
            input("\nPresiona ENTER para salir...")
        except EOFError:
            pass
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
        if str(ws.cell(row=1, column=col).value or "").strip() == header:
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
    log(f"💾 Excel actualizado → {excel_path} | Columna: {folder_name}")


# =========================
# SELENIUM
# =========================

def init_driver():
    """
    Abre Chrome usando el chromedriver descargado manualmente (ruta fija),
    evitando la auto-detección de Selenium Manager.
    """
    options = webdriver.ChromeOptions()

    # Solo se usa un Chrome específico si se configuró una ruta
    if CHROME_BINARY_PATH:
        if not os.path.exists(CHROME_BINARY_PATH):
            raise FileNotFoundError(
                f"No se encontró Chrome en: {CHROME_BINARY_PATH}\n"
                f"Verifica la ruta o déjala vacía para usar el Chrome instalado."
            )
        options.binary_location = CHROME_BINARY_PATH

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
    log("✅ Chrome iniciado con chromedriver manual")
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
# ESPERA DEL HTML FINAL
# =========================

def extract_fullsize_html(driver):
    try:
        for a in driver.find_elements(By.TAG_NAME, "textarea"):
            val = (a.get_attribute("value") or "").strip()
            lower = val.lower()
            if val and "<img" in val and "imgbox.com" in lower and "thumb" not in lower:
                return val
    except Exception:
        pass
    return ""


def esperar_html_final(driver):
    log("⌛ Esperando HTML FINAL...")
    while True:
        html = extract_fullsize_html(driver)
        if html:
            log("✅ HTML detectado")
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
        log(f"⚠️ Carpeta vacía: {folder}")
        return

    nombre_carpeta = os.path.basename(folder)

    log("\n📁 SUBCARPETA ACTUAL (RUTA COMPLETA):")
    log(folder)
    log(f"📦 Archivos: {len(archivos)}")

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
    codigo_salida = 0

    # --- Validar argumento ---
    if len(sys.argv) < 2:
        log("❌ No se recibió ruta del batch")
        log('Uso: python uploader.py "C:\\ruta\\al\\batch"')
        pausar_y_salir(1)

    batch_root = sys.argv[1]

    if not os.path.isdir(batch_root):
        log(f"❌ La ruta no existe o no es una carpeta: {batch_root}")
        pausar_y_salir(1)

    log("\n🚀 INICIANDO UPLOADER")
    log("📂 RUTA COMPLETA DEL BATCH:")
    log(batch_root)

    excel_path = get_excel_path(batch_root)
    log(f"📊 Excel del batch: {excel_path}")

    carpetas = obtener_subcarpetas(batch_root)
    log(f"📁 Total carpetas: {len(carpetas)}")

    if not carpetas:
        log("⚠️ No se encontraron subcarpetas en el batch. Nada que hacer.")
        pausar_y_salir(0)

    # --- Abrir Chrome con manejo de errores explícito ---
    try:
        driver = init_driver()
    except Exception:
        log("\n❌ ERROR CRÍTICO: no se pudo abrir Chrome")
        log(traceback.format_exc())
        pausar_y_salir(1)
        return

    try:
        for idx, carpeta in enumerate(carpetas, 1):
            log(f"\n➡️ {idx}/{len(carpetas)}")
            subir_carpeta(driver, excel_path, carpeta)

        log("\n🏁 BATCH COMPLETADO")

    except Exception:
        codigo_salida = 1
        log("\n❌ ERROR CRÍTICO DURANTE LA EJECUCIÓN")
        log(traceback.format_exc())

    finally:
        time.sleep(5)
        try:
            driver.quit()
        except Exception:
            pass
        log("✅ Proceso terminado")

    pausar_y_salir(codigo_salida)


if __name__ == "__main__":
    main()