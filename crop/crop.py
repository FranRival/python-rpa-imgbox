import os
from PIL import Image

# =========================
# CONFIGURACIÓN
# =========================

# Carpeta origen
CARPETA_ORIGEN = r"C:\Users\dell\Downloads\marca"

# Carpeta destino (Descargas)
CARPETA_DESTINO = r"C:\Users\dell\Downloads\lmi_recortadas"

PORCENTAJE_CORTE = 0.10   # 10% por lado
ANCHO_MINIMO = 600        # px
ALTO_MINIMO = 600         # px

EXTENSIONES = (".jpg", ".jpeg", ".png")

# =========================

def procesar_imagen(ruta_origen, ruta_destino):
    with Image.open(ruta_origen) as img:
        ancho, alto = img.size

        # Control de resolución mínima
        if ancho < ANCHO_MINIMO or alto < ALTO_MINIMO:
            print(f"⏭️  Saltada (muy pequeña): {ruta_origen}")
            return

        dx = int(ancho * PORCENTAJE_CORTE)
        dy = int(alto * PORCENTAJE_CORTE)

        # Seguridad extra
        if ancho - (dx * 2) < ANCHO_MINIMO or alto - (dy * 2) < ALTO_MINIMO:
            print(f"⏭️  Saltada (recorte inseguro): {ruta_origen}")
            return

        crop_box = (dx, dy, ancho - dx, alto - dy)
        img_recortada = img.crop(crop_box)

        # Crear carpeta destino si no existe
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)

        img_recortada.save(ruta_destino)
        print(f"✔ Guardada: {ruta_destino}")

def recorrer_carpeta():
    for root, _, files in os.walk(CARPETA_ORIGEN):
        for archivo in files:
            if archivo.lower().endswith(EXTENSIONES):

                ruta_origen = os.path.join(root, archivo)

                # Ruta relativa respecto a la carpeta origen
                ruta_relativa = os.path.relpath(ruta_origen, CARPETA_ORIGEN)

                # Ruta final en Descargas (estructura espejo)
                ruta_destino = os.path.join(CARPETA_DESTINO, ruta_relativa)

                try:
                    procesar_imagen(ruta_origen, ruta_destino)
                except Exception as e:
                    print(f"✖ Error en {ruta_origen}: {e}")

if __name__ == "__main__":
    recorrer_carpeta()
