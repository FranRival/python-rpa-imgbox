import os
from PIL import Image

# === CONFIG ===
carpeta_entrada = r"C:\Users\dell\Desktop\listo\101\AAA"
carpeta_salida = os.path.join(carpeta_entrada, "New")

max_ancho = 1200      # estándar recomendado
calidad = 75          # equilibrio perfecto

os.makedirs(carpeta_salida, exist_ok=True)

for archivo in os.listdir(carpeta_entrada):
    if archivo.lower().endswith((".jpg", ".jpeg", ".png")):
        ruta_entrada = os.path.join(carpeta_entrada, archivo)
        nombre_sin_ext = os.path.splitext(archivo)[0]
        ruta_salida = os.path.join(carpeta_salida, nombre_sin_ext + ".jpg")

        with Image.open(ruta_entrada) as img:
            img = img.convert("RGB")

            # Redimensionar SOLO si es más grande que el estándar
            if img.width > max_ancho:
                ratio = max_ancho / img.width
                nuevo_alto = int(img.height * ratio)
                img = img.resize((max_ancho, nuevo_alto), Image.LANCZOS)

            img.save(
                ruta_salida,
                "JPEG",
                quality=calidad,
                optimize=True,
                progressive=True,
                subsampling=2
            )

        peso_original = os.path.getsize(ruta_entrada) / 1024
        peso_nuevo = os.path.getsize(ruta_salida) / 1024

        print(f"{archivo} | {peso_original:.0f} KB → {peso_nuevo:.0f} KB")

print("Proceso terminado.")
