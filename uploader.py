import os
import sys
import time
import traceback
from pathlib import Path

# 🔥 EVITA BLOQUEOS DE CMD / .BAT
sys.stdin = open(os.devnull)

# 🔥 EVITA QUE CMD "TRAGUE" LOS PRINTS (buffering) — así se ven en tiempo real
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

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

def _elemento_visible_con_texto(driver, texto):
    """
    Chevereto precarga en el DOM todos los textos de estado (subiendo, completo,
    error, etc.) y solo los muestra/oculta con CSS. Por eso NO basta con
    'presence_of_element_located': hay que revisar que el elemento esté
    realmente visible (is_displayed()), si no se dispara un falso positivo
    apenas carga la página.
    """
    try:
        for el in driver.find_elements(By.XPATH, f"//*[contains(text(),'{texto}')]"):
            if el.is_displayed():
                return True
    except Exception:
        pass
    return False


def esperar_subida_completa(driver, timeout=300):
    print("⌛ Esperando a que la subida termine (Subida completa)...")
    fin = time.time() + timeout
    while time.time() < fin:
        if _elemento_visible_con_texto(driver, "Subida completa") and not _elemento_visible_con_texto(
            driver, "se está subiendo"
        ):
            print("✅ Subida completa detectada")
            return
        time.sleep(2)
    raise TimeoutException("La subida no terminó (no se detectó 'Subida completa' visible) a tiempo.")


# =========================
# PASO 4: ELEGIR "HTML completo con enlace" EN EL SELECT
# =========================

def seleccionar_html_completo(driver, timeout=180):
    """
    El select real es: <select id="form-embed-toggle"> con la opción
    <option value="html-embed-medium">HTML completo con enlace</option>
    (confirmado directamente del HTML de la página). Usamos el id y el value
    exactos en vez de buscar por texto, que es mucho más frágil.
    """
    print("🔍 Buscando el selector 'form-embed-toggle'...")
    fin = time.time() + timeout
    select_el = None
    intentos = 0

    while time.time() < fin:
        candidatos = driver.find_elements(By.ID, "form-embed-toggle")
        if candidatos:
            select_el = candidatos[0]
            break
        intentos += 1
        if intentos % 10 == 0:
            print(f"   ...siguen buscando el select ({intentos}s transcurridos)")
        time.sleep(1)

    if select_el is None:
        # Fallback por si el id cambiara en otra versión del sitio
        candidatos = driver.find_elements(By.XPATH, "//select[option[contains(.,'HTML completo')]]")
        if candidatos:
            select_el = candidatos[0]
            print("⚠️ No se encontró por id 'form-embed-toggle', se usó fallback por texto de opción.")
        else:
            selects = driver.find_elements(By.TAG_NAME, "select")
            print(f"⚠️ No se encontró ningún select válido. Selects en la página: {len(selects)}")
            for s in selects:
                try:
                    opciones = [o.text for o in s.find_elements(By.TAG_NAME, "option")]
                    print(f"   - id={s.get_attribute('id')} visible={s.is_displayed()} opciones={opciones}")
                except Exception:
                    pass
            raise TimeoutException("No se encontró el <select> de códigos de inserción a tiempo.")

    print(f"✅ Select encontrado (tras {intentos}s). Fijando value='html-embed-medium'...")

    driver.execute_script(
        """
        var select = arguments[0];
        select.value = 'html-embed-medium';
        select.dispatchEvent(new Event('change', { bubbles: true }));
        select.dispatchEvent(new Event('input', { bubbles: true }));
        if (typeof $ !== 'undefined' && $.fn.selectpicker) {
            $(select).selectpicker('val', 'html-embed-medium');
            $(select).selectpicker('refresh');
        }
        """,
        select_el,
    )
    time.sleep(1.5)

    # Verificamos si el truco de JS realmente actualizó el textarea visible.
    # Si el widget visual no reacciona al evento 'change' programático,
    # hacemos un FALLBACK: clic real sobre el desplegable y sobre la opción,
    # tal como lo haría una persona.
    if extraer_html_generado(driver):
        print("✅ El truco de JS funcionó directamente")
        return

    print("↪️ El truco de JS no actualizó el widget visual, probando clic real...")
    try:
        wrapper = select_el.find_element(By.XPATH, "./..")

        toggle = None
        for sel in (
            ".//button[contains(@class,'dropdown-toggle')]",
            ".//*[@data-toggle='dropdown']",
            ".//button",
        ):
            encontrados = wrapper.find_elements(By.XPATH, sel)
            if encontrados:
                toggle = encontrados[0]
                print(f"   toggle encontrado con selector: {sel}")
                break

        if toggle is None:
            raise NoSuchElementException("No se encontró botón toggle en el wrapper del select")

        driver.execute_script("arguments[0].click();", toggle)
        time.sleep(0.8)

        opcion = wrapper.find_element(
            By.XPATH, ".//*[contains(normalize-space(.),'HTML completo') and not(contains(normalize-space(.),'Miniatura'))]"
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opcion)
        driver.execute_script("arguments[0].click();", opcion)
        time.sleep(1.5)

        if extraer_html_generado(driver):
            print("✅ Fallback de clic visual funcionó")
        else:
            print("⚠️ Fallback de clic visual se ejecutó pero el textarea sigue sin el HTML esperado")
    except Exception as e:
        print(f"⚠️ Fallback de clic visual también falló: {e}")


# =========================
# PASO 5: EXTRAER EL HTML GENERADO
# =========================

def extraer_html_generado(driver):
    """
    Busca, entre todos los <textarea> de la página, el que contiene el código
    'HTML completo con enlace' (formato <a href="..."><img src="..."></a>)
    apuntando a los dominios de freeimage.host / iili.io.

    OJO: tanto la versión completa ('html-embed-medium') como la miniatura
    ('html-embed-thumbnail') tienen esa misma forma <a><img>. Por eso, si hay
    varias coincidencias, se prioriza la que tenga ".md." en la URL (sufijo de
    tamaño "medium" que usa freeimage.host), y si ninguna lo tiene, se devuelve
    la primera coincidencia igual.
    """
    candidatas = []
    try:
        for area in driver.find_elements(By.TAG_NAME, "textarea"):
            val = (area.get_attribute("value") or "").strip()
            if not val:
                continue
            lower = val.lower()
            if "<img" in lower and "<a href" in lower and any(d in lower for d in DOMINIOS_VALIDOS):
                candidatas.append(val)
    except Exception:
        pass

    if not candidatas:
        return ""

    for val in candidatas:
        if ".md." in val.lower():
            return val

    return candidatas[0]


def esperar_html_final(driver, timeout=180):
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