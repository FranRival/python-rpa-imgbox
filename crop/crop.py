import os
from PIL import Image

# =========================
# CONFIGURACIÓN
# =========================

CARPETA_MADRE = "imagenes"

PORCENTAJE_CORTE = 0.10      # 10% por lado
ANCHO_MINIMO = 600           # px
ALTO_MINIMO = 600            # px

BACKUP = True                # crea copia antes de modificar
EXTENSIONES = (".jpg", ".jpeg", ".png")

# =========================

def procesar_imagen(ruta):
    with Image.open(ruta) as img:
        ancho, alto = img.size

        # Control de resolución mínima
        if ancho < ANCHO_MINIMO or alto < ALTO_MINIMO:
            print(f"⏭️  Saltada (muy pequeña): {ruta} ({ancho}x{alto})")
            return

        dx = int(ancho * PORCENTAJE_CORTE)
        dy = int(alto * PORCENTAJE_CORTE)

        # Evita recortes absurdos
        if ancho - (dx * 2) < ANCHO_MINIMO or alto - (dy * 2) < ALTO_MINIMO:
            print(f"⏭️  Saltada (recorte inseguro): {ruta}")
            return

        crop_box = (
            dx,            # izquierda
            dy,            # arriba
            ancho - dx,    # derecha
            alto - dy      # abajo
        )

        img_recortada = img.crop(crop_box)

        # Backup
        if BACKUP:
            backup_path = ruta + ".bak"
            if not os.path.exists(backup_path):
                img.save(backup_path)

        img_recortada.save(ruta)
        print(f"✔ Procesada: {ruta}")

def recorrer_carpeta(carpeta):
    for root, _, files in os.walk(carpeta):
        for archivo in files:
            if archivo.lower().endswith(EXTENSIONES):
                ruta_completa = os.path.join(root, archivo)
                try:
                    procesar_imagen(ruta_completa)
                except Exception as e:
                    print(f"✖ Error en {ruta_completa}: {e}")

if __name__ == "__main__":
    recorrer_carpeta(CARPETA_MADRE)
