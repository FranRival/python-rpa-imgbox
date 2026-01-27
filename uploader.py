import os, time, csv, traceback, sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openpyxl import load_workbook, Workbook

# ============ CONFIG =============
EXCEL_PATH = r"C:\Users\dell\Desktop\resultado_embeds.xlsx"
SHEET_NAME = "Sheet1"
OUTPUT_CSV = "results.csv"
IMGBOX_URL = "https://imgbox.com/upload"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}
MAX_WAIT_SECONDS = 900
RETRIES_PER_FOLDER = 2
DELAY_BETWEEN_FOLDS = 2
# ==================================


# ✅ ROOT_FOLDER ahora viene dinámicamente desde orquestador
if len(sys.argv) < 2:
    print("❌ No se recibió la ruta del batch")
    sys.exit(1)

ROOT_FOLDER = sys.argv[1]
print("\n📁 ROOT_FOLDER dinámico:", ROOT_FOLDER)


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
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
    start_url = driver.current_url
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            areas = driver.find_elements(By.TAG_NAME, "textarea")
            for a in areas:
                val = (a.get_attribute("value") or a.text or "").strip()
                if val and "<a " in val and "<img " in val and "imgbox.com" in val:
                    return True

            dones = driver.find_elements(By.CSS_SELECTOR, ".upload-done")
            for d in dones:
                cls = d.get_attribute("class") or ""
                if "hidden" not in cls:
                    return True

            if driver.current_url != start_url:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def extract_fullsize_html(driver):
    try:
        candidates = []
        areas = driver.find_elements(By.TAG_NAME, "textarea")
        for a in areas:
            val = (a.get_attribute("value") or a.text or "").strip()
            if not val:
                continue
            if "<a " in val and "<img " in val and "imgbox.com" in val:
                lower = val.lower()
                if "images" in lower and "thumb" not in lower:
                    candidates.append(val)

        if not candidates:
            return ""

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
    max_col = ws.max_column
    for col in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col)
        if (cell.value or "").strip() == header_text:
            return col
    new_col = max_col + 1
    ws.cell(row=1, column=new_col, value=header_text)
    return new_col


def write_html_to_excel(path, sheet_name, header_text, html_text):
    wb = ensure_excel(path, sheet_name)
    col = find_or_add_column_for_header(wb, sheet_name, header_text)
    ws = wb[sheet_name]
    ws.cell(row=2, column=col, value=html_text)
    wb.save(path)


def process_folder_once(driver, folder_path):
    try:
        files = gather_files(folder_path)
        if not files:
            return ("no_files", 0, "", "")

        driver.get(IMGBOX_URL)
        wait = WebDriverWait(driver, 30)

        input_sel = (
            ".select-files-button-large input[type='file'], "
            ".fileinput-button input[type='file'], "
            "span.fileinput-button input[type='file'], "
            "input[type='file']"
        )
        input_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, input_sel)))
        input_el.send_keys("\n".join(files))

        start_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#fake-submit-button"))
        )
        driver.execute_script("arguments[0].click();", start_btn)

        finished = wait_for_upload_finish(driver)
        html = extract_fullsize_html(driver)

        return ("ok", len(files), html, "")

    except Exception:
        return ("error", 0, "", traceback.format_exc())


def main():
    driver = init_driver()

    new_csv = not os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvf:
        writer = csv.DictWriter(csvf, fieldnames=["folder", "files_count", "status", "error"])
        if new_csv:
            writer.writeheader()

        for entry in sorted(os.listdir(ROOT_FOLDER)):
            folder_path = os.path.join(ROOT_FOLDER, entry)
            if not os.path.isdir(folder_path):
                continue

            print(f"\n📂 Procesando: {folder_path}")

            status, files_count, html_result, error_msg = process_folder_once(driver, folder_path)

            if html_result:
                write_html_to_excel(EXCEL_PATH, SHEET_NAME, entry, html_result)

            writer.writerow({
                "folder": folder_path,
                "files_count": files_count,
                "status": status,
                "error": error_msg
            })
            csvf.flush()

            time.sleep(DELAY_BETWEEN_FOLDS)

    print("\n✅ Batch finalizado correctamente")
    input("Presiona ENTER para cerrar uploader...")


if __name__ == "__main__":
    main()
