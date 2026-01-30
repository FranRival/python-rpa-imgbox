import os
import sys
import time
import traceback
from pathlib import Path

# 🔥 EVITA BLOQUEOS DE CMD / .BAT
sys.stdin = open(os.devnull)

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

IMGBOX_URL = "https://imgbox.com/upload"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}


# =========================
# UTILIDADES
# =========================

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

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
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

    print(f"\n📁 Subiendo: {nombre_carpeta}")
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
    if len(sys.argv) < 2:
        print("❌ No se recibió ruta del batch")
        sys.exit(1)

    batch_root = sys.argv[1]

    print("\n🚀 INICIANDO UPLOADER")
    print(f"📂 Batch activo: {batch_root}")

    excel_path = get_excel_path(batch_root)
    print(f"📊 Excel del batch: {excel_path}")

    carpetas = obtener_subcarpetas(batch_root)
    print(f"📁 Total carpetas: {len(carpetas)}")

    driver = init_driver()

    try:
        for idx, carpeta in enumerate(carpetas, 1):
            print(f"\n➡️ {idx}/{len(carpetas)}")
            subir_carpeta(driver, excel_path, carpeta)

        print("\n🏁 BATCH COMPLETADO")

    except Exception:
        print("\n❌ ERROR CRÍTICO")
        traceback.print_exc()

    finally:
        time.sleep(5)
        driver.quit()
        print("✅ Proceso terminado")


if __name__ == "__main__":
    main()
