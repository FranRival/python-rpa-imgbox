"""
uploader_imgbox_full_xlsx.py

Automatiza:
 - Por cada subcarpeta en ROOT_FOLDER:
   1) abre https://imgbox.com/upload
   2) selecciona todos los archivos de la carpeta
   3) selecciona Adult Content (value 2)
   4) pulsa Start upload
   5) espera a que termine la subida (espera inteligente)
   6) extrae el HTML-FULL-SIZE resultante
   7) pega ese HTML en un archivo Excel: busca columna cuyo header (fila 1) coincide con el nombre de la carpeta y escribe en fila 2
Salida:
 - results.csv con registro (folder, files_count, status, error)
Notas:
 - Requiere: selenium, webdriver-manager, openpyxl
"""

import os, time, csv, traceback
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openpyxl import load_workbook, Workbook

# ============ CONFIG =============
ROOT_FOLDER = r"C:\Users\dell\Downloads\Natalie Roush\New folder\[aaa]"
EXCEL_PATH = r"C:\Users\dell\Desktop\resultado_embeds.xlsx"   # si no existe, se creará
SHEET_NAME = "Sheet1"
OUTPUT_CSV = "results.csv"
IMGBOX_URL = "https://imgbox.com/upload"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}
MAX_WAIT_SECONDS = 900   # max por carpeta (ajusta según tu conexión)
RETRIES_PER_FOLDER = 2
DELAY_BETWEEN_FOLDS = 2  # segundos entre carpetas
# ==================================

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # evita cierre automático para depuración
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=service, options=options)
    drv.set_page_load_timeout(60)
    return drv

def gather_files(folder_path):
    files = []
    for f in sorted(os.listdir(folder_path)):
        full = os.path.join(folder_path, f)
        if os.path.isfile(full) and Path(full).suffix.lower() in ALLOWED_EXT:
            files.append(full)
    return files

def wait_for_upload_finish(driver, timeout=MAX_WAIT_SECONDS):
    """Espera dinámicamente a que ImgBox genere el HTML final o termine la upload."""
    start_url = driver.current_url
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            # 1) textareas que probablemente contengan embed html
            # buscamos cualquier textarea grande con <a href and <img
            areas = driver.find_elements(By.TAG_NAME, "textarea")
            for a in areas:
                val = (a.get_attribute("value") or a.text or "").strip()
                if val and "<a " in val and "<img " in val and "imgbox.com" in val:
                    return True

            # 2) clase .upload-done visible
            dones = driver.find_elements(By.CSS_SELECTOR, ".upload-done")
            for d in dones:
                cls = d.get_attribute("class") or ""
                if "hidden" not in cls:
                    return True

            # 3) cambio de URL
            if driver.current_url != start_url:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

def extract_fullsize_html(driver):
    """
    Extrae exclusivamente el HTML-FULL-SIZE.
    Regla:
        - Debe contener: <a ...><img ...>
        - Debe contener dominio: images*.imgbox.com (o 'images' en la URL)
        - No debe contener 'thumb' ni 'thumbs'
    Devuelve string o ''.
    """
    try:
        candidates = []

        # 1) Buscar todas las textareas y filtrar por reglas FULL SIZE
        areas = driver.find_elements(By.TAG_NAME, "textarea")
        for a in areas:
            val = (a.get_attribute("value") or a.text or "").strip()
            if not val:
                continue
            # Debe contener enlaces y tags de imagen
            if "<a " in val and "<img " in val and "imgbox.com" in val:
                # Preferir las que contienen 'images' y no 'thumb'
                lower = val.lower()
                if "images" in lower and "thumb" not in lower:
                    candidates.append(val)

        # 2) Si no encontramos en textareas, buscar en '.embed-code' u otros selectores
        if not candidates:
            embeds = driver.find_elements(By.CSS_SELECTOR, ".embed-code textarea, textarea.embed, .image-embed textarea")
            for a in embeds:
                val = (a.get_attribute("value") or a.text or "").strip()
                if not val:
                    continue
                lower = val.lower()
                if "<a " in val and "<img " in val and "imgbox.com" in val and "images" in lower and "thumb" not in lower:
                    candidates.append(val)

        # 3) Si aún no hay candidatos (casos raros), intentar cualquier textarea que tenga imgbox.com pero evitar thumbs
        if not candidates:
            for a in driver.find_elements(By.TAG_NAME, "textarea"):
                val = (a.get_attribute("value") or a.text or "").strip()
                if not val:
                    continue
                lower = val.lower()
                if "imgbox.com" in lower and "thumb" not in lower:
                    # preferir bloques que contengan <a and <img
                    if "<a " in val and "<img " in val:
                        candidates.append(val)

        # 4) Si no hay ninguno, devolver vacío
        if not candidates:
            return ""

        # Devolver la más larga (full-size suele ser la más extensa)
        candidates.sort(key=lambda s: len(s), reverse=True)
        return candidates[0]

    except Exception:
        return ""

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

def find_or_add_column_for_header(wb, sheet_name, header_text):
    ws = wb[sheet_name]
    # read headers in row 1
    max_col = ws.max_column
    for col in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col)
        if (cell.value or "").strip() == header_text:
            return col
    # not found: append new column at end
    new_col = max_col + 1
    ws.cell(row=1, column=new_col, value=header_text)
    return new_col

def write_html_to_excel(path, sheet_name, header_text, html_text):
    wb = ensure_excel(path, sheet_name)
    col = find_or_add_column_for_header(wb, sheet_name, header_text)
    ws = wb[sheet_name]
    # write into row 2 of that column
    ws.cell(row=2, column=col, value=html_text)
    wb.save(path)

def process_folder_once(driver, folder_path):
    """Procesa una carpeta: sube, selecciona adult, inicia upload, espera y extrae HTML.
       Devuelve tuple(status, files_count, html, error_message)"""
    try:
        files = gather_files(folder_path)
        if not files:
            return ("no_files", 0, "", "")
        driver.get(IMGBOX_URL)
        wait = WebDriverWait(driver, 30)

        # localizar input file real (varios selectores posibles)
        input_sel = (".select-files-button-large input[type='file'], "
                     ".fileinput-button input[type='file'], "
                     "span.fileinput-button input[type='file'], "
                     "input[type='file']")
        input_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, input_sel)))
        # enviar archivos
        file_string = "\n".join(files)
        input_el.send_keys(file_string)

        # --- seleccionar Content Type = Adult (robusto) ---
        # intentamos primero asignar value en el select oculto y refrescar selectpicker
        success_ct = False
        last_err = None
        try:
            ct = WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.ID, "dropdown-content-type")))
        except Exception:
            ct = None

        if ct:
            try:
                driver.execute_script("arguments[0].value = '2';", ct)
                driver.execute_script("""
                    try {
                        var e = new Event('change', { bubbles: true });
                        arguments[0].dispatchEvent(e);
                    } catch(err) {}
                    try {
                        if (typeof $ !== 'undefined' && typeof $.fn.selectpicker !== 'undefined') {
                            $('#dropdown-content-type').selectpicker('val','2');
                            $('#dropdown-content-type').selectpicker('refresh');
                        }
                    } catch(err2) {}
                """, ct)
                time.sleep(0.6)
                v = ct.get_attribute("value")
                if v == "2" or v == 2:
                    success_ct = True
            except Exception as e:
                last_err = e

        # fallback visual click into dropdown if needed
        if not success_ct:
            try:
                # abrir visual dropdown
                dropdown_btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-id='dropdown-content-type']"))
                )
                dropdown_btn.click()
                time.sleep(0.4)
                # intentar li[rel='2'] o li con text 'Adult Content'
                try:
                    adult_li = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.dropdown-menu.inner.selectpicker li[rel='2']"))
                    )
                except Exception:
                    adult_li = None
                if adult_li:
                    driver.execute_script("arguments[0].click();", adult_li)
                    time.sleep(0.4)
                    # verify hidden select
                    try:
                        ct_check = driver.find_element(By.ID, "dropdown-content-type")
                        if ct_check.get_attribute("value") == "2":
                            success_ct = True
                    except Exception:
                        success_ct = True
                else:
                    # last resort: click 3rd li
                    possible = driver.find_elements(By.CSS_SELECTOR, "ul.dropdown-menu.inner.selectpicker li")
                    if len(possible) >= 3:
                        driver.execute_script("arguments[0].click();", possible[2])
                        time.sleep(0.3)
                        success_ct = True
            except Exception as e:
                last_err = e

        if not success_ct:
            # one more JS attempt
            try:
                driver.execute_script("""
                    var s = document.getElementById('dropdown-content-type') || document.querySelector('select[name=\"content-type\"]');
                    if (s) { s.value = '2'; var ev = new Event('change', {bubbles:true}); s.dispatchEvent(ev); }
                    try{ if (typeof $ !== 'undefined' && $.fn.selectpicker) { $('#dropdown-content-type').selectpicker('val','2'); $('#dropdown-content-type').selectpicker('refresh'); } } catch(e){}
                """)
                time.sleep(0.5)
                try:
                    ct_final = driver.find_element(By.ID, "dropdown-content-type")
                    if ct_final.get_attribute("value") == "2":
                        success_ct = True
                except Exception:
                    pass
            except Exception as e:
                last_err = e

        if not success_ct:
            return ("no_ct_selected", len(files), "", f"ct_error: {str(last_err)}")

        # --- pulsar Start upload (fake-submit-button) ---
        try:
            start_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#fake-submit-button, button#fake-submit-button"))
            )
            driver.execute_script("arguments[0].click();", start_btn)
        except Exception as e:
            # fallback: botón por texto
            try:
                btns = driver.find_elements(By.XPATH, "//button[contains(normalize-space(.), 'Start upload') or contains(normalize-space(.), 'Start Upload') or contains(normalize-space(.), 'Start')]")
                if btns:
                    driver.execute_script("arguments[0].click();", btns[0])
                else:
                    return ("no_start_button", len(files), "", str(e))
            except Exception as e2:
                return ("no_start_button", len(files), "", str(e2))

        # esperar dinamicamente
        finished = wait_for_upload_finish(driver, timeout=MAX_WAIT_SECONDS)
        if not finished:
            # try to still extract anything
            html = extract_fullsize_html(driver)
            return ("timeout", len(files), html, "timeout_wait")
        # extract HTML
        html = extract_fullsize_html(driver)
        return ("ok" if html else "ok_no_embeds", len(files), html, "")
    except Exception as exc:
        return ("error", 0, "", traceback.format_exc())

def main():
    driver = init_driver()

    # prepare CSV
    new_csv = not os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvf:
        writer = csv.DictWriter(csvf, fieldnames=["folder", "files_count", "status", "error"])
        if new_csv:
            writer.writeheader()

        # iterate subfolders
        for entry in sorted(os.listdir(ROOT_FOLDER)):
            folder_path = os.path.join(ROOT_FOLDER, entry)
            if not os.path.isdir(folder_path):
                continue
            print(f"Processing folder: {folder_path}")
            attempt = 0
            result_status = None
            files_count = 0
            html_result = ""
            error_msg = ""
            while attempt <= RETRIES_PER_FOLDER:
                attempt += 1
                status, files_count, html_result, error_msg = process_folder_once(driver, folder_path)
                print(f"  attempt {attempt}: status={status}")
                if status == "ok" or status == "ok_no_embeds" or status == "no_files":
                    result_status = status
                    break
                else:
                    print(f"   -> retry (status {status}), error: {error_msg}")
                    time.sleep(3 + attempt * 2)
            if result_status is None:
                result_status = status

            # write html into excel (if any) at header matching 'entry' (folder name)
            try:
                if html_result:
                    write_html_to_excel(EXCEL_PATH, SHEET_NAME, entry, html_result)
                    print("  HTML written to Excel for column header:", entry)
                else:
                    print("  No HTML extracted for folder:", entry)
            except Exception as e:
                print("  Error writing to Excel:", e)

            writer.writerow({
                "folder": folder_path,
                "files_count": files_count,
                "status": result_status,
                "error": error_msg
            })
            csvf.flush()
            print("  Logged result:", result_status)
            time.sleep(DELAY_BETWEEN_FOLDS)

    print("All done. Browser remains open for inspection. Close manually when ready.")
    input("Press ENTER to quit (this will close the script but Chrome remains open)...")

if __name__ == "__main__":
    main()
