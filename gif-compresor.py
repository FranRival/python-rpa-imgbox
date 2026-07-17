#!/usr/bin/env python3
"""
comprimir_gifs.py

Recorre una carpeta madre (y TODAS sus subcarpetas) buscando archivos .gif
que pesen más que un límite (por defecto 9.5 MB) y crea, EN LA MISMA
CARPETA donde vive cada GIF, una versión comprimida con el sufijo
"-optimizado" en el nombre.

Ejemplo:
    /carpeta_madre/sub1/animacion.gif             (original, sin tocar)
    /carpeta_madre/sub1/animacion-optimizado.gif  (nuevo, ya liviano)

- El archivo original NUNCA se borra ni se modifica.
- Los .jpg/.jpeg/.png no se tocan.
- Si un GIF ya pesa menos del límite, NO se crea copia (no hace falta
  duplicarlo); se deja tal cual.

Estrategia de compresión (se detiene apenas el archivo queda por debajo
del límite):
    1. gifsicle con --lossy creciente + reducción de colores (mejor
       relación calidad/peso).
    2. Si gifsicle no está instalado, usa Pillow como respaldo: reduce
       colores, reduce tamaño (escala) y elimina fotogramas alternos.

Requisitos:
    pip install Pillow
    (opcional pero MUY recomendado) instalar gifsicle:
        - Ubuntu/Debian: sudo apt-get install gifsicle
        - macOS:         brew install gifsicle
        - Windows:       https://eternallybored.org/misc/gifsicle/
                          (descargar el .exe y poner su carpeta en el PATH)
"""

import os
import shutil
import subprocess

# ============================ CONFIGURACIÓN ============================

# Carpeta madre que contiene las 500 subcarpetas con tus GIFs
CARPETA_ORIGEN = r"C:\Users\dell\Downloads\Newfolder"

# Peso máximo permitido, en MB (el servidor pide menos de 10 MB)
LIMITE_MB = 9.5  # dejo un pequeño margen de seguridad respecto a los 10 MB

# Sufijo que se agrega al nombre del archivo comprimido
SUFIJO = "-optimizado"

# Si vuelves a correr el script y ya existe el archivo "-optimizado",
# ponlo en True para volver a generarlo desde cero (por si cambiaste LIMITE_MB)
REEMPLAZAR_SI_YA_EXISTE = False

# =========================================================================

LIMITE_BYTES = LIMITE_MB * 1024 * 1024
GIFSICLE_DISPONIBLE = shutil.which("gifsicle") is not None
TIMEOUT_POR_INTENTO = 60  # segundos máximos por cada intento de gifsicle


def tamano_mb(ruta):
    return os.path.getsize(ruta) / (1024 * 1024)


def _run_gifsicle(args, destino, limite_bytes):
    """Corre gifsicle con timeout de seguridad. Devuelve True si ya cumple el límite."""
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=TIMEOUT_POR_INTENTO)
    except subprocess.TimeoutExpired:
        print("    (intento tardó demasiado, se omite y se prueba con más compresión)")
        return False
    except subprocess.CalledProcessError as e:
        print(f"    (gifsicle falló en un intento: {e})")
        return False
    return os.path.exists(destino) and os.path.getsize(destino) <= limite_bytes


def comprimir_con_gifsicle(origen, destino, limite_bytes):
    """
    Comprime en pasos progresivos combinando --lossy, --colors y --scale.
    Se detiene apenas el archivo queda por debajo del límite.
    """
    if _run_gifsicle(["gifsicle", "-O3", origen, "-o", destino], destino, limite_bytes):
        return True

    pasos = [
        (60, 256, None),
        (100, 128, None),
        (150, 64, None),
        (150, 64, 0.75),
        (200, 32, 0.6),
        (200, 32, 0.45),
        (200, 16, 0.3),
    ]

    for lossy, colores, escala in pasos:
        args = ["gifsicle", "-O3", f"--lossy={lossy}", "--colors", str(colores)]
        if escala is not None:
            args += [f"--scale={escala}"]
        args += [origen, "-o", destino]
        if _run_gifsicle(args, destino, limite_bytes):
            return True

    return os.path.exists(destino) and os.path.getsize(destino) <= limite_bytes


def comprimir_con_pillow(origen, destino, limite_bytes):
    """Respaldo si no hay gifsicle: reduce colores, escala y fotogramas con Pillow."""
    from PIL import Image, ImageSequence

    def guardar(frames, duraciones, escala, colores, saltar_frames):
        frames_finales = frames[::saltar_frames] if saltar_frames > 1 else frames
        dur_finales = duraciones[::saltar_frames] if saltar_frames > 1 else duraciones

        procesados = []
        for fr in frames_finales:
            f = fr.convert("RGBA")
            if escala != 1.0:
                nuevo_tam = (max(1, int(f.width * escala)), max(1, int(f.height * escala)))
                f = f.resize(nuevo_tam, Image.LANCZOS)
            f = f.convert("P", palette=Image.ADAPTIVE, colors=colores)
            procesados.append(f)

        procesados[0].save(
            destino, save_all=True, append_images=procesados[1:],
            duration=dur_finales, loop=0, optimize=True, disposal=2
        )

    with Image.open(origen) as im:
        frames, duraciones = [], []
        for frame in ImageSequence.Iterator(im):
            frames.append(frame.copy())
            duraciones.append(frame.info.get("duration", 100))

    combinaciones = [
        (1.0, 128, 1), (1.0, 64, 1), (0.8, 64, 1), (0.8, 64, 2),
        (0.6, 32, 2), (0.5, 32, 3), (0.4, 16, 3),
    ]
    for escala, colores, saltar in combinaciones:
        guardar(frames, duraciones, escala, colores, saltar)
        if os.path.getsize(destino) <= limite_bytes:
            return True

    return os.path.getsize(destino) <= limite_bytes


def ruta_optimizada(ruta_gif):
    """Genera la ruta del archivo comprimido en la MISMA carpeta, con el sufijo."""
    carpeta, nombre = os.path.split(ruta_gif)
    base, ext = os.path.splitext(nombre)
    return os.path.join(carpeta, f"{base}{SUFIJO}{ext}")


def procesar_gif(ruta_gif):
    destino = ruta_optimizada(ruta_gif)

    if os.path.exists(destino) and not REEMPLAZAR_SI_YA_EXISTE:
        print(f"  Omitido (ya existe): {destino}")
        return

    peso_original = tamano_mb(ruta_gif)

    if peso_original <= LIMITE_MB:
        print(f"  Sin cambios (ya cumple, {peso_original:.2f} MB): {ruta_gif}")
        return

    try:
        if GIFSICLE_DISPONIBLE:
            exito = comprimir_con_gifsicle(ruta_gif, destino, LIMITE_BYTES)
        else:
            exito = comprimir_con_pillow(ruta_gif, destino, LIMITE_BYTES)
    except Exception as e:
        print(f"  ERROR procesando {ruta_gif}: {e}")
        return

    peso_final = tamano_mb(destino)
    estado = "OK" if exito else "NO SE LOGRÓ BAJAR DEL LIMITE"
    print(f"  {estado}: {destino}  ({peso_original:.2f} MB -> {peso_final:.2f} MB)")


def main():
    if not GIFSICLE_DISPONIBLE:
        print("Aviso: gifsicle no está instalado. Se usará Pillow como respaldo")
        print("(funciona, pero gifsicle suele dar mejor calidad con menor peso).")
        print("Para instalarlo: sudo apt-get install gifsicle  |  brew install gifsicle\n")

    total = 0
    for raiz, _dirs, archivos in os.walk(CARPETA_ORIGEN):
        for nombre in archivos:
            if not nombre.lower().endswith(".gif"):
                continue
            if nombre.lower().endswith(f"{SUFIJO}.gif"):
                continue  # evita re-procesar un archivo ya optimizado

            total += 1
            procesar_gif(os.path.join(raiz, nombre))

    print(f"\nListo. Se revisaron {total} GIF(s).")


if __name__ == "__main__":
    main()