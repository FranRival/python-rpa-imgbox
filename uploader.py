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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from openpyxl import Workbook, load_workbook


# =========================
# CONFIGURACIÓN
# =========================

FREEIMAGE_URL = "https://freeimage.host/es-mx"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}  # freeimage.host no acepta .mp4

# Dominios válidos que puede devolver el HTML generado (freeimage.host usa iili.io como CDN)
DOMINIOS_VALIDOS = ("freeimage.host", "iili.io")


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
    # Evita el diálogo nativo "guardar contraseña" / notificaciones que puedan tapar botones
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2
    })
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def cerrar_popups(driver):
    """Cierra banners de cookies u overlays que puedan bloquear clics."""
    posibles_textos = ["Aceptar", "Accept", "OK", "Entendido"]
    for texto in posibles_textos:
        try:
            btn = driver.find_element(
                By.XPATH, f"//button[contains(normalize-space(.),'{texto}')]"
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)
        except NoSuchElementException:
            pass


# =========================
# PASO 1: SELECCIONAR ARCHIVOS
# =========================

def seleccionar_archivos(driver, archivos):
    wait = WebDriverWait(driver, 30)
    input_file = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
    )
    # No hace falta que sea visible para send_keys en Selenium con Chrome
    input_file.send_keys("\n".join(archivos))
    time.sleep(2)


# =========================
# PASO 2: CLIC EN BOTÓN VERDE "SUBIR"
# =========================

def click_boton_subir(driver):
    wait = WebDriverWait(driver, 30)

    # El botón verde "Subir" aparece SOLO después de cargar miniaturas en la cola.
    # Se busca por texto exacto de <button> para no confundirlo con el link "Subir" del menú superior.
    boton = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space(text())='Subir']")
        )
    )
    driver.execute_script("arguments[0].click();", boton)


# =========================
# PASO 3: ESPERAR "SUBIDA COMPLETA"
# =========================

def esperar_subida_completa(driver, timeout=300):
    print("⌛ Esperando a que la subida termine (Subida completa)...")
    wait = WebDriverWait(driver, timeout)
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'Subida completa')]")
        )
    )
    print("✅ Subida completa detectada")


# =========================
# PASO 4: ELEGIR "HTML completo con enlace" EN EL SELECT
# =========================

def seleccionar_html_completo(driver):
    wait = WebDriverWait(driver, 30)

    select_el = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//select[option[contains(text(),'HTML completo con enlace')]]")
        )
    )

    sel = Select(select_el)
    sel.select_by_visible_text("HTML completo con enlace")
    time.sleep(1.5)  # da tiempo a que el textarea se actualice via JS


# =========================
# PASO 5: EXTRAER EL HTML GENERADO
# =========================

def extraer_html_generado(driver):
    """
    Busca, entre todos los <textarea> de la página, el que contiene el código
    'HTML completo con enlace' (formato <a href="..."><img src="..."></a>)
    apuntando a los dominios de freeimage.host / iili.io.
    """
    try:
        for area in driver.find_elements(By.TAG_NAME, "textarea"):
            val = (area.get_attribute("value") or "").strip()
            if not val:
                continue
            lower = val.lower()
            if "<img" in lower and "<a href" in lower and any(d in lower for d in DOMINIOS_VALIDOS):
                return val
    except Exception:
        pass
    return ""


def esperar_html_final(driver, timeout=60):
    print("⌛ Esperando HTML FINAL en el textarea...")
    fin = time.time() + timeout
    while time.time() < fin:
        html = extraer_html_generado(driver)
        if html:
            print("✅ HTML detectado")
            return html
        time.sleep(2)
    raise TimeoutException("No se detectó el HTML generado a tiempo.")


# =========================
# PROCESO DE SUBIDA POR CARPETA
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

    driver.get(FREEIMAGE_URL)
    time.sleep(3)
    cerrar_popups(driver)

    seleccionar_archivos(driver, archivos)
    click_boton_subir(driver)
    esperar_subida_completa(driver)
    seleccionar_html_completo(driver)

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

    print("\n🚀 INICIANDO UPLOADER (freeimage.host)")
    print("📂 RUTA COMPLETA DEL BATCH:")
    print(batch_root)

    excel_path = get_excel_path(batch_root)
    print(f"📊 Excel del batch: {excel_path}")

    carpetas = obtener_subcarpetas(batch_root)
    print(f"📁 Total carpetas: {len(carpetas)}")

    driver = init_driver()

    try:
        for idx, carpeta in enumerate(carpetas, 1):
            print(f"\n➡️ {idx}/{len(carpetas)}")
            try:
                subir_carpeta(driver, excel_path, carpeta)
            except Exception:
                print(f"\n❌ ERROR en la carpeta: {carpeta}")
                traceback.print_exc()
                continue  # sigue con la siguiente carpeta en vez de morir todo el batch

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