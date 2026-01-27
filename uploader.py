import os
import time
import traceback
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from openpyxl import Workbook, load_workbook


# =========================
# CONFIGURACIÓN
# =========================
RUTA_BATCH_TXT = r"C:\Users\dell\Desktop\batch-ruta.txt"
IMGBOX_URL = "https://imgbox.com/upload"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}

EXCEL_PATH = r"C:\Users\dell\Desktop\result.xlsx"
SHEET_NAME = "Sheet1"


# =========================
# UTILIDADES
# =========================

def leer_ruta_actual():
    with open(RUTA_BATCH_TXT, "r", encoding="utf-8") as f:
        ruta = f.readline().strip()
    if not ruta or not os.path.isdir(ruta):
        raise Exception(f"Ruta inválida en batch-ruta.txt: {ruta}")
    return ruta


def obtener_subcarpetas(root):
    return [
        os.path.join(root, d)
        for d in sorted(os.listdir(root))
        if os.path.isdir(os.path.join(root, d))
    ]


# =========================
# EXCEL
# =========================

def ensure_excel(path, sheet_name):
    if not os.path.exists(path):
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        wb.save(path)

    wb = load_workbook(path)
    if sheet_name not in wb.sheetnames:
        wb.create_sheet(sheet_name)

    return wb


def find_or_create_column(wb, sheet_name, header):
    ws = wb[sheet_name]
    max_col = ws.max_column

    for col in range(1, max_col + 1):
        if (ws.cell(row=1, column=col).value or "").strip() == header:
            return col

    new_col = max_col + 1
    ws.cell(row=1, column=new_col, value=header)
    return new_col


def write_html_to_excel(header, html):
    wb = ensure_excel(EXCEL_PATH, SHEET_NAME)
    ws = wb[SHEET_NAME]

    col = find_or_create_column(wb, SHEET_NAME, header)
    ws.cell(row=2, column=col, value=html)

    wb.save(EXCEL_PATH)
    print(f"💾 HTML guardado en Excel → columna: {header}")


# =========================
# SELENIUM
# =========================

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def seleccionar_adult_content(driver):
    print("🔞 Forzando Adult Content (JS)...")
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
    print("✅ Adult Content configurado")


# =========================
# ESPERA REAL SIN TIMEOUT
# =========================

def extract_fullsize_html(driver):
    try:
        areas = driver.find_elements(By.TAG_NAME, "textarea")
        for a in areas:
            val = (a.get_attribute("value") or "").strip()
            lower = val.lower()
            if (
                val
                and "<a " in val
                and "<img " in val
                and "imgbox.com" in lower
                and "thumb" not in lower
            ):
                return val
    except:
        pass

    return ""


def esperar_html_final(driver):
    print("⌛ Esperando HTML FINAL (sin timeout)...")

    while True:
        html = extract_fullsize_html(driver)
        if html:
            print("✅ HTML detectado — subida confirmada")
            return html

        time.sleep(3)


# =========================
# PROCESO PRINCIPAL
# =========================

def subir_carpeta(driver, folder):
    archivos = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if Path(f).suffix.lower() in ALLOWED_EXT
    ]

    if not archivos:
        print(f"⚠️ Carpeta vacía: {folder}")
        return

    nombre_carpeta = os.path.basename(folder)

    print(f"\n📁 Subiendo carpeta: {nombre_carpeta}")
    print(f"📦 Archivos: {len(archivos)}")

    driver.get(IMGBOX_URL)
    time.sleep(3)

    seleccionar_adult_content(driver)

    wait = WebDriverWait(driver, 30)
    input_file = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
    )

    print("📤 Enviando archivos...")
    input_file.send_keys("\n".join(archivos))
    time.sleep(2)

    print("🚀 Iniciando upload...")
    start_btn = wait.until(
        EC.element_to_be_clickable((By.ID, "fake-submit-button"))
    )
    driver.execute_script("arguments[0].click();", start_btn)

    # 🔥 Espera real
    html = esperar_html_final(driver)

    write_html_to_excel(nombre_carpeta, html)


def main():
    print("\n🚀 INICIANDO UPLOADER")

    root = leer_ruta_actual()
    print(f"📂 Batch activo: {root}")

    carpetas = obtener_subcarpetas(root)
    print(f"📊 Total de carpetas a subir: {len(carpetas)}")

    driver = init_driver()

    try:
        for idx, carpeta in enumerate(carpetas, 1):
            print("\n==============================")
            print(f"➡️ Carpeta {idx}/{len(carpetas)}")
            subir_carpeta(driver, carpeta)

        print("\n🏁 TODAS LAS CARPETAS DEL BATCH FINALIZADAS")

    except Exception:
        print("\n❌ ERROR CRÍTICO:")
        traceback.print_exc()

    finally:
        print("\n🧹 Cerrando navegador...")
        time.sleep(5)
        driver.quit()
        print("✅ Proceso terminado correctamente")


if __name__ == "__main__":
    main()
