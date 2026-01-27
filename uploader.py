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


# =========================
# CONFIGURACIÓN
# =========================
RUTA_BATCH_TXT = r"C:\Users\dell\Desktop\batch-ruta.txt"
IMGBOX_URL = "https://imgbox.com/upload"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}


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


def contar_archivos(folder):
    return sum(
        1 for f in os.listdir(folder)
        if Path(f).suffix.lower() in ALLOWED_EXT
    )


def calcular_timeout_dinamico(num_files):
    base = 300
    por_imagen = 2
    maximo = 2400
    estimado = base + (num_files * por_imagen)
    return min(estimado, maximo)


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
    print("✅ Adult Content forzado")


def esperar_html_final(driver, timeout):
    print(f"⌛ Esperando HTML final ({int(timeout/60)} min máximo)...")
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            areas = driver.find_elements(By.TAG_NAME, "textarea")
            for a in areas:
                val = (a.get_attribute("value") or "").lower()
                if "<a " in val and "<img " in val and "imgbox.com" in val:
                    print("✅ HTML detectado — subida finalizada")
                    return True
        except:
            pass

        time.sleep(2)

    print("⛔ Timeout esperando HTML")
    return False


# =========================
# PROCESO
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

    timeout = calcular_timeout_dinamico(len(archivos))

    print(f"\n📁 Subiendo carpeta: {folder}")
    print(f"📦 Archivos: {len(archivos)}")
    print(f"⏱️ Timeout asignado: {int(timeout/60)} minutos")

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

    esperar_html_final(driver, timeout)


def main():
    print("\n🚀 INICIANDO UPLOADER")

    root = leer_ruta_actual()
    print(f"📂 Batch activo: {root}")

    carpetas = obtener_subcarpetas(root)
    print(f"📊 Total de carpetas a subir: {len(carpetas)}")

    driver = init_driver()

    try:
        for idx, carpeta in enumerate(carpetas, 1):
            print(f"\n==============================")
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
