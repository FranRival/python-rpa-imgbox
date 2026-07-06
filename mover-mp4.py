import os
import shutil

# Ruta de la carpeta madre
carpeta_madre = r"C:\Users\dell\Downloads\ps\1"

for carpeta_actual, _, archivos in os.walk(carpeta_madre):
    # Evita procesar la carpeta madre
    if carpeta_actual == carpeta_madre:
        continue

    for archivo in archivos:
        if archivo.lower().endswith(".mp4"):
            origen = os.path.join(carpeta_actual, archivo)
            destino = os.path.join(carpeta_madre, archivo)

            # Si ya existe un archivo con el mismo nombre,
            # agrega un número al final.
            if os.path.exists(destino):
                nombre, extension = os.path.splitext(archivo)
                contador = 1
                while True:
                    nuevo_nombre = f"{nombre}_{contador}{extension}"
                    destino = os.path.join(carpeta_madre, nuevo_nombre)
                    if not os.path.exists(destino):
                        break
                    contador += 1

            shutil.move(origen, destino)
            print(f"Movido: {origen} -> {destino}")

print("Proceso terminado.")