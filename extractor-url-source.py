
import os
from html.parser import HTMLParser

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA_MADRE = r"C:\Users\dell\Downloads\desc\links3"

ARCHIVO_SALIDA = os.path.join(
    CARPETA_MADRE,
    "urls extraidas.txt"
)


# ==========================================
# EXTRACTOR DE CANONICAL
# ==========================================

class CanonicalParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):

        if tag.lower() != "link":
            return

        atributos = dict(attrs)

        rel = atributos.get("rel", "").lower()
        href = atributos.get("href", "")

        if "canonical" in rel.split() and href:
            self.urls.append(href)


# ==========================================
# SCRAPER DE CARPETAS
# ==========================================

urls_extraidas = []
archivos_encontrados = 0
carpetas_revisadas = 0

for raiz, carpetas, archivos in os.walk(CARPETA_MADRE):

    carpetas_revisadas += 1

    for archivo in archivos:

        if archivo.lower() == "source" or archivo.lower() == "source.html":

            ruta_archivo = os.path.join(raiz, archivo)
            archivos_encontrados += 1

            try:
                with open(
                    ruta_archivo,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    contenido = f.read()

                parser = CanonicalParser()
                parser.feed(contenido)

                for url in parser.urls:
                    urls_extraidas.append(url)

                    print(f"[OK] {url}")

            except Exception as e:
                print(f"[ERROR] {ruta_archivo}: {e}")


# ==========================================
# GUARDAR RESULTADOS
# ==========================================

with open(
    ARCHIVO_SALIDA,
    "w",
    encoding="utf-8"
) as archivo:

    archivo.write("\n".join(urls_extraidas))

    if urls_extraidas:
        archivo.write("\n")


# ==========================================
# RESUMEN
# ==========================================

print("\n========== RESULTADOS ==========")
print(f"Carpetas revisadas: {carpetas_revisadas}")
print(f"Archivos source encontrados: {archivos_encontrados}")
print(f"URLs extraídas: {len(urls_extraidas)}")
print(f"Archivo generado: {ARCHIVO_SALIDA}")
print("================================")
