import os
import sys
import shutil
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# ================= CONFIG =================
DRY_RUN = False
MIN_BYTES = 1024

BASURA_PATTERNS = re.compile(
    r"(apple|touch|icon|placeholder|mx|sprite|thumb|logo|\d{2,4}x\d{2,4})",
    re.IGNORECASE
)

# ==========================================

# 🔹 Soporte para icono en .exe (PyInstaller)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # Cuando está empaquetado
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def log(msg):
    output.insert(tk.END, msg + "\n")
    output.see(tk.END)
    root.update()


def ensure_basura_dir(root_dir):
    basura_dir = os.path.join(root_dir, "basura")
    os.makedirs(basura_dir, exist_ok=True)
    return basura_dir


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


def mover_a_basura(src, basura_dir):
    name = os.path.basename(src)
    dst = os.path.join(basura_dir, name)

    base, ext = os.path.splitext(dst)
    counter = 1
    while os.path.exists(dst):
        dst = f"{base}_{counter}{ext}"
        counter += 1

    shutil.move(src, dst)
    log(f"   🗑️ Basura movida: {dst}")


def mover_seguro(src, dst):
    base, ext = os.path.splitext(dst)
    counter = 1

    while os.path.exists(dst):
        dst = f"{base}_{counter}{ext}"
        counter += 1

    shutil.move(src, dst)


def procesar_carpeta_post(post_path, basura_dir):
    log(f"\n📂 Procesando: {post_path}")

    # Aplanar subcarpetas
    for item in os.listdir(post_path):
        item_path = os.path.join(post_path, item)

        if os.path.isdir(item_path):
            log(f"   🔽 Aplanando subcarpeta: {item}")

            for file in os.listdir(item_path):
                src = os.path.join(item_path, file)
                dst = os.path.join(post_path, file)

                if os.path.isfile(src):
                    mover_seguro(src, dst)

            try:
                shutil.rmtree(item_path)
                log(f"   🗑️ Subcarpeta eliminada")
            except Exception as e:
                log(f"   ⚠️ Error borrando carpeta: {e}")

    # Mover basura
    for file in os.listdir(post_path):
        file_path = os.path.join(post_path, file)

        if not os.path.isfile(file_path):
            continue

        if es_basura(file, file_path):
            mover_a_basura(file_path, basura_dir)


def ejecutar():
    root_dir = ruta_entry.get().strip()

    if not os.path.isdir(root_dir):
        messagebox.showerror("Error", "Ruta inválida")
        return

    output.delete(1.0, tk.END)
    log("🚀 Iniciando limpieza...\n")

    basura_dir = ensure_basura_dir(root_dir)

    for folder in os.listdir(root_dir):
        folder_path = os.path.join(root_dir, folder)

        if folder.lower() == "basura":
            continue

        if not os.path.isdir(folder_path):
            continue

        procesar_carpeta_post(folder_path, basura_dir)

    log("\n✅ Limpieza finalizada.")
    messagebox.showinfo("Listo", "Proceso terminado.")


def seleccionar_carpeta():
    folder = filedialog.askdirectory()
    if folder:
        ruta_entry.delete(0, tk.END)
        ruta_entry.insert(0, folder)


# ================= GUI =================

root = tk.Tk()
root.title("Limpieza de Carpetas")
root.geometry("700x500")

# 🔹 Intentar cargar icono
try:
    root.iconbitmap(resource_path("icon.ico"))
except:
    pass

frame = tk.Frame(root)
frame.pack(pady=10)

ruta_entry = tk.Entry(frame, width=60)
ruta_entry.pack(side=tk.LEFT, padx=5)

btn_browse = tk.Button(frame, text="Seleccionar", command=seleccionar_carpeta)
btn_browse.pack(side=tk.LEFT)

btn_run = tk.Button(root, text="Ejecutar Limpieza", command=ejecutar, bg="green", fg="white")
btn_run.pack(pady=10)

output = scrolledtext.ScrolledText(root, width=80, height=20)
output.pack(padx=10, pady=10)

root.mainloop()