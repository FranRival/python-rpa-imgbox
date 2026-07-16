import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
import time
import csv

# =====================================================
# CONFIGURACIÓN
# =====================================================
URL = "https://www.--"
ARCHIVO_SALIDA_HTML = "sitio_completo.html"
CARPETA_IMAGENES = "imagenes_full"
ARCHIVO_REPORTE = "reporte_descargas.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

SESION = requests.Session()
SESION.headers.update(HEADERS)

# Patrón que identifica un thumbnail y una imagen full en la URL
PATRON_THUMB = "/images/thumb/"
PATRON_FULL = "/images/full/"

DELAY_ENTRE_PAGINAS = 1     # segundos, entre páginas de galería
DELAY_ENTRE_DETALLES = 0.5  # segundos, entre páginas de detalle de cada foto


# =====================================================
# FUNCIONES DE RED
# =====================================================
def obtener_html(url, referer=None):
    try:
        headers_extra = {"Referer": referer} if referer else {}
        respuesta = SESION.get(url, headers=headers_extra, timeout=20)
        respuesta.raise_for_status()
        return respuesta.text
    except Exception as e:
        print(f"    [ERROR] No se pudo descargar {url}: {e}")
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
# PAGINACIÓN (galería)
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
# PASO 1: encontrar links de detalle (/photo/{id}/...) en la galería
# =====================================================
def extraer_paginas_detalle(soup, url_pagina):
    """
    Devuelve lista de (id_foto, url_detalle) a partir de los <a> que envuelven
    thumbnails y apuntan a /photo/{id}/...
    """
    encontrados = []
    vistos = set()

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        src_abs = urljoin(url_pagina, src)
        if PATRON_THUMB not in src_abs:
            continue

        padre = img.find_parent("a")
        if not padre or not padre.get("href"):
            continue

        href_abs = urljoin(url_pagina, padre["href"])
        if href_abs in vistos:
            continue

        # id de la foto: preferimos el atributo name/id del <a>, si no, del <td>/<img>
        id_foto = padre.get("name") or img.get("id") or os.path.basename(urlparse(src_abs).path)

        vistos.add(href_abs)
        encontrados.append((id_foto, href_abs))

    return encontrados


# =====================================================
# PASO 2: en la página de detalle, extraer la URL full real
# =====================================================
def extraer_url_full_de_detalle(html_detalle, url_detalle):
    if not html_detalle:
        return None

    soup = BeautifulSoup(html_detalle, "html.parser")

    # 1) Buscar <img> cuyo src contenga el patrón de full
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src and PATRON_FULL in src:
            return urljoin(url_detalle, src)

    # 2) Buscar <a href> que contenga el patrón de full
    for a in soup.find_all("a", href=True):
        if PATRON_FULL in a["href"]:
            return urljoin(url_detalle, a["href"])

    # 3) Fallback: buscar con regex en todo el HTML crudo (por si está en JS/JSON)
    match = re.search(
        r'https?://[^\s"\'<>]+' + re.escape(PATRON_FULL) + r'[^\s"\'<>]+',
        html_detalle
    )
    if match:
        return match.group(0)

    return None


def nombre_archivo_desde_url(url):
    ruta = urlparse(url).path
    nombre = os.path.basename(ruta)
    return nombre if nombre else f"imagen_{abs(hash(url))}.jpg"


# =====================================================
# PROCESO PRINCIPAL
# =====================================================
def procesar_sitio():
    os.makedirs(CARPETA_IMAGENES, exist_ok=True)

    visitadas_galeria = set()
    ids_ya_descargados = set()
    reporte = []  # filas para el CSV

    url = URL

    with open(ARCHIVO_SALIDA_HTML, "w", encoding="utf-8") as archivo_html:
        while url and url not in visitadas_galeria:
            print(f"\nGalería: {url}")
            visitadas_galeria.add(url)

            html = obtener_html(url)
            if html is None:
                reporte.append([url, "GALERIA", "", "ERROR", "no se pudo descargar la página"])
                break

            archivo_html.write("\n<!-- ====================================================== -->\n")
            archivo_html.write(f"<!-- URL: {url} -->\n")
            archivo_html.write("<!-- ====================================================== -->\n\n")
            archivo_html.write(html)
            archivo_html.write("\n\n")

            soup = BeautifulSoup(html, "html.parser")

            # --- Paso 1: links de detalle ---
            paginas_detalle = extraer_paginas_detalle(soup, url)
            print(f"  Fotos encontradas en esta galería: {len(paginas_detalle)}")

            for id_foto, url_detalle in paginas_detalle:
                if id_foto in ids_ya_descargados:
                    continue
                ids_ya_descargados.add(id_foto)

                # --- Paso 2: visitar detalle y extraer URL full ---
                html_detalle = obtener_html(url_detalle, referer=url)
                time.sleep(DELAY_ENTRE_DETALLES)

                if html_detalle is None:
                    reporte.append([url_detalle, "DETALLE", "", "ERROR", "no se pudo descargar página de detalle"])
                    continue

                url_full = extraer_url_full_de_detalle(html_detalle, url_detalle)
                if not url_full:
                    print(f"    [AVISO] No se encontró URL full para foto {id_foto}")
                    reporte.append([url_detalle, "IMAGEN", "", "NO_ENCONTRADA", f"id={id_foto}"])
                    continue

                nombre = nombre_archivo_desde_url(url_full)
                ruta_destino = os.path.join(CARPETA_IMAGENES, nombre)

                base, ext = os.path.splitext(ruta_destino)
                contador = 1
                while os.path.exists(ruta_destino):
                    ruta_destino = f"{base}_{contador}{ext}"
                    contador += 1

                # Referer = la página de detalle (como haría un navegador real al hacer clic)
                ok, error = descargar_archivo(url_full, ruta_destino, referer=url_detalle)
                if ok:
                    print(f"    [OK] {id_foto} -> {ruta_destino}")
                    reporte.append([url_detalle, "IMAGEN", url_full, "OK", ""])
                else:
                    print(f"    [ERROR] {id_foto} -> {error}")
                    reporte.append([url_detalle, "IMAGEN", url_full, "ERROR", error])

            # --- siguiente página de galería ---
            siguiente = encontrar_siguiente(soup, url)
            if siguiente in visitadas_galeria:
                break
            url = siguiente
            time.sleep(DELAY_ENTRE_PAGINAS)

    with open(ARCHIVO_REPORTE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pagina_origen", "tipo", "url_recurso", "estado", "detalle"])
        writer.writerows(reporte)

    print("\n" + "=" * 55)
    print("Proceso terminado.")
    print(f"Galerías visitadas: {len(visitadas_galeria)}")
    print(f"Fotos únicas procesadas: {len(ids_ya_descargados)}")
    print(f"Imágenes descargadas: {sum(1 for r in reporte if r[3] == 'OK')}")
    print(f"Errores: {sum(1 for r in reporte if r[3] == 'ERROR')}")
    print(f"No encontradas: {sum(1 for r in reporte if r[3] == 'NO_ENCONTRADA')}")
    print(f"HTML guardado en: {ARCHIVO_SALIDA_HTML}")
    print(f"Imágenes guardadas en: {CARPETA_IMAGENES}/")
    print(f"Reporte detallado: {ARCHIVO_REPORTE}")


if __name__ == "__main__":
    procesar_sitio()