import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("❌ Debes pasar la ruta como parámetro")
        sys.exit(1)

    ROOT_FOLDER = sys.argv[1]
    print("📁 Carpeta activa:", ROOT_FOLDER)

    carpeta = Path(ROOT_FOLDER)

    if not carpeta.exists():
        print("❌ La carpeta no existe:", ROOT_FOLDER)
        sys.exit(1)

    # =====================================================
    # 👉 PEGA AQUÍ TU CÓDIGO REAL DE SUBIDA
    # Todo debe usar ROOT_FOLDER dinámicamente
    # =====================================================

    print("⬆️ Subiendo imágenes...")
    # tu código actual aquí

    print("📊 Generando Excel...")
    # tu código actual aquí

    print("✅ Batch finalizado correctamente")
    return


if __name__ == "__main__":
    main()
