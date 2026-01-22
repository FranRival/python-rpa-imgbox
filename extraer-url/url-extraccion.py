import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import time

# =========================
# CONFIG
# =========================

START_URL = "https://www.poringa.net/buscar/?q=%40CarlitoxxxEspia"
POST_PATTERN = "/posts/imagenes/"
OUTPUT_FILE = "links.txt"
MAX_PAGES = 14          # límite de seguridad
SLEEP_SECONDS = 1.2      # pausa entre requests
MAX_EMPTY_PAGES = 3      # cortar si ya no hay contenido nuevo

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# =========================
# SCRAPER
# =========================

def extract_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    found = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_url, href)

        if POST_PATTERN in full_url:
            found.add(full_url)

    return found


def build_page_url(base_url, page):
    # Si la URL ya tiene parámetros, añadimos &p=
    if "?" in base_url:
        return f"{base_url}&p={page}"
    else:
        return f"{base_url}?p={page}"


def main():
    all_links = set()
    empty_pages = 0

    print("\n🚀 Iniciando scraping con paginación ?p=\n")

    for page in range(1, MAX_PAGES + 1):
        page_url = build_page_url(START_URL, page)
        print(f"📄 Página {page} → {page_url}")

        try:
            response = requests.get(page_url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print("⚠️ Página no válida, cortando.")
                break

        except Exception as e:
            print("❌ Error de conexión:", e)
            break

        page_links = extract_links(response.text, page_url)
        new_links = page_links - all_links

        if not new_links:
            empty_pages += 1
            print("⚠️ No hay links nuevos.")

            if empty_pages >= MAX_EMPTY_PAGES:
                print("\n🛑 Varias páginas sin contenido nuevo. Finalizando.")
                break
        else:
            empty_pages = 0
            all_links.update(new_links)
            print(f"✅ Nuevos links encontrados: {len(new_links)}")
            print(f"📦 Total acumulado: {len(all_links)}")

        time.sleep(SLEEP_SECONDS)

    # =========================
    # SAVE FILE
    # =========================

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for link in sorted(all_links):
            f.write(link + "\n")

    print("\n✅ Scraping terminado.")
    print(f"📄 Total final: {len(all_links)} links guardados en {OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()
