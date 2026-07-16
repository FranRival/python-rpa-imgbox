import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time
import csv

# =====================================================
# CONFIGURACIÓN
# =====================================================
URL = "https://browerstar.com"
ARCHIVO_SALIDA_HTML = "sitio_completo.html"
CARPETA_IMAGENES = "imagenes_full"
ARCHIVO_REPORTE = "reporte_descargas.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

# Sesión compartida para mantener cookies entre peticiones (algunos CDNs lo exigen)
SESION = requests.Session()
SESION.headers.update(HEADERS)

# Patrón que identifica un thumbnail en la URL. Ajusta si tu sitio usa otro nombre
# (p.ej. "/thumbs/", "/small/", "-thumb", etc.)
PATRON_THUMB = "/thumb/"
PATRON_FULL = "/full/"

# Extensiones de imagen que nos interesan
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".gif", ".webp")

DELAY_ENTRE_PAGINAS = 1  # segundos, para no saturar el servidor


# =====================================================
# FUNCIONES DE RED
# =====================================================
def obtener_html(url):
    try:
        respuesta = SESION.get(url, timeout=20)
        respuesta.raise_for_status()
        return respuesta.text
    except Exception as e:
        print(f"  [ERROR] No se pudo descargar página {url}: {e}")
        return None


def descargar_archivo(url, ruta_destino, referer=None):
    try:
        headers_extra = {"Referer": referer} if referer else {}
        respuesta = SESION.get(url, headers=headers_extra, timeout=30, stream=True)
        respuesta.raise_for_status()
        with open(ruta_destino, "wb") as f:
            for chunk in respuesta.iter_content(chunk_size=8192):
                f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)


# =====================================================
# PAGINACIÓN (tu lógica original)
# =====================================================
def encontrar_siguiente(soup, url_actual):
    link = soup.find("link", rel="next")
    if link and link.get("href"):
        return urljoin(url_actual, link["href"])

    a = soup.find("a", rel="next")
    if a and a.get("href"):
        return urljoin(url_actual, a["href"])

    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if "/page/" in href:
            return urljoin(url_actual, href)

    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if "page=" in href:
            return urljoin(url_actual, href)

    return None


# =====================================================
# LÓGICA DE THUMBNAIL -> FULL
# =====================================================
def es_thumbnail(src_url):
    return PATRON_THUMB in src_url


def convertir_a_full_por_patron(url_thumb):
    """Fallback: intenta transformar la URL cambiando /thumb/ por /full/."""
    if PATRON_THUMB in url_thumb:
        return url_thumb.replace(PATRON_THUMB, PATRON_FULL)
    return None


def extraer_urls_full(soup, url_pagina):
    """
    Devuelve una lista de (url_full, metodo) encontradas en la página.
    metodo: 'href_ancla' o 'patron_reemplazo'
    """
    encontradas = []
    vistos = set()

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue

        src_abs = urljoin(url_pagina, src)

        if not es_thumbnail(src_abs):
            continue  # no nos interesa si no parece thumbnail

        url_full = None
        metodo = None

        # Prioridad 1: <a href="..."> que envuelve el <img>
        padre = img.find_parent("a")
        if padre and padre.get("href"):
            href_abs = urljoin(url_pagina, padre["href"])
            if href_abs.lower().endswith(EXTENSIONES_IMAGEN):
                url_full = href_abs
                metodo = "href_ancla"

        # Prioridad 2 (fallback): reemplazo de patrón en la URL
        if url_full is None:
            candidata = convertir_a_full_por_patron(src_abs)
            if candidata:
                url_full = candidata
                metodo = "patron_reemplazo"

        if url_full and url_full not in vistos:
            vistos.add(url_full)
            encontradas.append((url_full, metodo))

    return encontradas


def nombre_archivo_desde_url(url):
    ruta = urlparse(url).path
    nombre = os.path.basename(ruta)
    return nombre if nombre else f"imagen_{abs(hash(url))}.jpg"


# =====================================================
# PROCESO PRINCIPAL
# =====================================================
def procesar_sitio():
    os.makedirs(CARPETA_IMAGENES, exist_ok=True)

    visitadas = set()
    imagenes_descargadas = set()
    reporte = []  # filas para el CSV

    url = URL

    with open(ARCHIVO_SALIDA_HTML, "w", encoding="utf-8") as archivo_html:
        while url and url not in visitadas:
            print(f"\nPágina: {url}")
            visitadas.add(url)

            html = obtener_html(url)
            if html is None:
                reporte.append([url, "PAGINA", "", "ERROR", "no se pudo descargar la página"])
                break

            archivo_html.write("\n<!-- ====================================================== -->\n")
            archivo_html.write(f"<!-- URL: {url} -->\n")
            archivo_html.write("<!-- ====================================================== -->\n\n")
            archivo_html.write(html)
            archivo_html.write("\n\n")

            soup = BeautifulSoup(html, "html.parser")

            # --- extraer y descargar imágenes full ---
            urls_full = extraer_urls_full(soup, url)
            print(f"  Imágenes full encontradas: {len(urls_full)}")

            for url_full, metodo in urls_full:
                if url_full in imagenes_descargadas:
                    continue
                imagenes_descargadas.add(url_full)

                nombre = nombre_archivo_desde_url(url_full)
                ruta_destino = os.path.join(CARPETA_IMAGENES, nombre)

                # Evitar sobrescribir si ya existe un archivo con el mismo nombre
                base, ext = os.path.splitext(ruta_destino)
                contador = 1
                while os.path.exists(ruta_destino):
                    ruta_destino = f"{base}_{contador}{ext}"
                    contador += 1

                ok, error = descargar_archivo(url_full, ruta_destino, referer=url)
                if ok:
                    print(f"    [OK] ({metodo}) {url_full}")
                    reporte.append([url, "IMAGEN", url_full, "OK", metodo])
                else:
                    print(f"    [ERROR] ({metodo}) {url_full} -> {error}")
                    reporte.append([url, "IMAGEN", url_full, "ERROR", error])

            # --- siguiente página ---
            siguiente = encontrar_siguiente(soup, url)
            if siguiente in visitadas:
                break
            url = siguiente
            time.sleep(DELAY_ENTRE_PAGINAS)

    # Guardar reporte CSV
    with open(ARCHIVO_REPORTE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pagina_origen", "tipo", "url_recurso", "estado", "detalle"])
        writer.writerows(reporte)

    print("\n" + "=" * 55)
    print("Proceso terminado.")
    print(f"Páginas visitadas: {len(visitadas)}")
    print(f"Imágenes descargadas: {sum(1 for r in reporte if r[3] == 'OK')}")
    print(f"Errores: {sum(1 for r in reporte if r[3] == 'ERROR')}")
    print(f"HTML guardado en: {ARCHIVO_SALIDA_HTML}")
    print(f"Imágenes guardadas en: {CARPETA_IMAGENES}/")
    print(f"Reporte detallado: {ARCHIVO_REPORTE}")


if __name__ == "__main__":
    procesar_sitio()