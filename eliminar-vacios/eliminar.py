import os
import shutil

# =========================
# CONFIGURACIÓN
# =========================

CARPETA_MADRE = r"C:\Users\dell\Downloads\marzo\aaa\17"
NOMBRE_BASURA = "basura"
ARCHIVO_OBJETIVO = "source.html"

# =========================

def limpiar_carpetas():
    carpeta_basura = os.path.join(CARPETA_MADRE, NOMBRE_BASURA)
    os.makedirs(carpeta_basura, exist_ok=True)

    for nombre in os.listdir(CARPETA_MADRE):
        ruta_carpeta = os.path.join(CARPETA_MADRE, nombre)

        # Ignorar si no es carpeta o es la carpeta basura
        if not os.path.isdir(ruta_carpeta):
            continue
        if nombre == NOMBRE_BASURA:
            continue

        archivos = os.listdir(ruta_carpeta)

        # Condición exacta: SOLO un archivo y es source.html
        if len(archivos) == 1 and archivos[0].lower() == ARCHIVO_OBJETIVO.lower():
            destino = os.path.join(carpeta_basura, nombre)

            print(f"🗑 Moviendo: {ruta_carpeta}")
            shutil.move(ruta_carpeta, destino)
        else:
            print(f"✔ Conservada: {ruta_carpeta}")

if __name__ == "__main__":
    limpiar_carpetas()
