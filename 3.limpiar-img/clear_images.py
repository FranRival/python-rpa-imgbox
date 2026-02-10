import os
import shutil
import re

# ================= CONFIG =================
ROOT_DIR = r"C:\Users\dell\Downloads\marzo\aaa\112"
BASURA_DIR = os.path.join(ROOT_DIR, "basura")

DRY_RUN = False   # True = simula | False = ejecuta
MIN_BYTES = 1024  # 1 KB

BASURA_PATTERNS = re.compile(
    r"(apple|touch|icon|placeholder|mx|sprite|thumb|logo|\d{2,4}x\d{2,4})",
    re.IGNORECASE
)

# ==========================================


def ensure_basura_dir():
    if DRY_RUN:
        print(f"[SIMULADO] Crear carpeta basura: {BASURA_DIR}")
    else:
        os.makedirs(BASURA_DIR, exist_ok=True)


def es_basura(filename, fullpath):
    try:
        size = os.path.getsize(fullpath)
    except:
        return True

    if size < MIN_BYTES:
        return True

    if BASURA_PATTERNS.search(filename):
        return True

    return False


def mover_a_basura(src):
    name = os.path.basename(src)
    dst = os.path.join(BASURA_DIR, name)

    base, ext = os.path.splitext(dst)
    counter = 1
    while os.path.exists(dst):
        dst = f"{base}_{counter}{ext}"
        counter += 1

    if DRY_RUN:
        print(f"[SIMULADO] Basura: {src} → {dst}")
    else:
        shutil.move(src, dst)
        print(f"   🗑️ Basura movida: {dst}")


def mover_seguro(src, dst):
    base, ext = os.path.splitext(dst)
    counter = 1

    while os.path.exists(dst):
        dst = f"{base}_{counter}{ext}"
        counter += 1

    if DRY_RUN:
        print(f"[SIMULADO] {src} → {dst}")
    else:
        shutil.move(src, dst)


def procesar_carpeta_post(post_path):
    print(f"\n📂 Procesando: {post_path}")

    # ---------- 1. Aplanar subcarpetas ----------
    for item in os.listdir(post_path):
        item_path = os.path.join(post_path, item)

        if os.path.isdir(item_path):
            print(f"   🔽 Aplanando subcarpeta: {item}")

            for file in os.listdir(item_path):
                src = os.path.join(item_path, file)
                dst = os.path.join(post_path, file)

                if os.path.isfile(src):
                    mover_seguro(src, dst)

            # eliminar subcarpeta vacía
            if DRY_RUN:
                print(f"   [SIMULADO] Borrar carpeta: {item_path}")
            else:
                try:
                    shutil.rmtree(item_path)
                    print(f"   🗑️ Subcarpeta eliminada")
                except Exception as e:
                    print(f"   ⚠️ Error borrando carpeta: {e}")

    # ---------- 2. Mover basura ----------
    for file in os.listdir(post_path):
        file_path = os.path.join(post_path, file)

        if not os.path.isfile(file_path):
            continue

        if es_basura(file, file_path):
            mover_a_basura(file_path)


# ================= EJECUCIÓN =================

print("🚀 Iniciando limpieza...\n")
ensure_basura_dir()

for folder in os.listdir(ROOT_DIR):
    folder_path = os.path.join(ROOT_DIR, folder)

    # Ignorar carpeta basura
    if folder.lower() == "basura":
        continue

    if not os.path.isdir(folder_path):
        continue

    procesar_carpeta_post(folder_path)

print("\n✅ Limpieza finalizada.")
