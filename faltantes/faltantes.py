import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox


def procesar(txt_path):
    if not os.path.isfile(txt_path):
        messagebox.showerror("Error", "El archivo faltantes.txt no existe.")
        return

    base_dir = os.path.dirname(os.path.abspath(txt_path))
    destino = os.path.join(base_dir, "Faltantes")
    os.makedirs(destino, exist_ok=True)

    with open(txt_path, "r", encoding="utf-8") as f:
        nombres_validos = set(line.strip() for line in f if line.strip())

    movidas = []
    omitidas = []

    for item in os.listdir(base_dir):
        ruta_item = os.path.join(base_dir, item)

        if os.path.isdir(ruta_item) and item != "Faltantes":
            if item not in nombres_validos:
                destino_final = os.path.join(destino, item)

                if not os.path.exists(destino_final):
                    shutil.move(ruta_item, destino_final)
                    movidas.append(item)
                else:
                    omitidas.append(item)

    resultado = f"""
Proceso terminado.

Carpetas movidas:
{movidas}

Carpetas omitidas (ya existían):
{omitidas}
"""
    messagebox.showinfo("Resultado", resultado)


def seleccionar_archivo():
    archivo = filedialog.askopenfilename(
        title="Selecciona faltantes.txt",
        filetypes=[("Archivos TXT", "*.txt")]
    )
    if archivo:
        entry_ruta.delete(0, tk.END)
        entry_ruta.insert(0, archivo)


def ejecutar():
    ruta = entry_ruta.get().strip().strip('"')
    procesar(ruta)


# ----------------- INTERFAZ -----------------

root = tk.Tk()
root.title("Mover Carpetas Faltantes")
root.geometry("500x180")
root.resizable(False, False)

label = tk.Label(root, text="Ruta de faltantes.txt:")
label.pack(pady=5)

entry_ruta = tk.Entry(root, width=60)
entry_ruta.pack(pady=5)

btn_examinar = tk.Button(root, text="Examinar", command=seleccionar_archivo)
btn_examinar.pack(pady=5)

btn_procesar = tk.Button(root, text="Procesar", command=ejecutar, bg="#4CAF50", fg="white")
btn_procesar.pack(pady=10)

root.mainloop()