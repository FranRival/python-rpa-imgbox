#!/usr/bin/env python3
"""
Extractor de URLs con interfaz gráfica.
1) Pega el código fuente completo.
2) Escribe el prefijo de la URL (puedes poner varios separados por espacio).
3) Pulsa "Procesar".
"""
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

URL_REGEX = re.compile(r"""https?://[^\s"'<>\\)\]}]+""", re.IGNORECASE)


def extraer_urls(texto, prefijos):
    vistas, resultado = set(), []
    for url in URL_REGEX.findall(texto):
        url = url.rstrip(".,;")
        if any(url.startswith(p) for p in prefijos) and url not in vistas:
            vistas.add(url)
            resultado.append(url)
    return resultado


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Extractor de URLs")
        self.geometry("900x700")
        self.minsize(700, 500)

        marco = ttk.Frame(self, padding=10)
        marco.pack(fill="both", expand=True)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(1, weight=3)
        marco.rowconfigure(5, weight=2)

        ttk.Label(marco, text="1. Pega aquí el código fuente completo:").grid(row=0, column=0, sticky="w")
        self.txt_codigo = scrolledtext.ScrolledText(marco, wrap="none", height=15)
        self.txt_codigo.grid(row=1, column=0, sticky="nsew", pady=(2, 8))

        ttk.Label(marco, text="2. Pega aquí la URL (prefijo) con la que deben comenzar:").grid(row=2, column=0, sticky="w")
        self.ent_prefijo = ttk.Entry(marco)
        self.ent_prefijo.grid(row=3, column=0, sticky="ew", pady=(2, 8))

        barra = ttk.Frame(marco)
        barra.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(barra, text="Procesar", command=self.procesar).pack(side="left")
        ttk.Button(barra, text="Copiar resultado", command=self.copiar).pack(side="left", padx=6)
        ttk.Button(barra, text="Guardar .txt", command=self.guardar).pack(side="left")
        ttk.Button(barra, text="Limpiar", command=self.limpiar).pack(side="left", padx=6)
        self.lbl_estado = ttk.Label(barra, text="")
        self.lbl_estado.pack(side="right")

        self.txt_resultado = scrolledtext.ScrolledText(marco, wrap="none", height=10)
        self.txt_resultado.grid(row=5, column=0, sticky="nsew")

    def procesar(self):
        codigo = self.txt_codigo.get("1.0", "end")
        prefijos = self.ent_prefijo.get().split()
        if not codigo.strip():
            messagebox.showwarning("Falta código", "Pega primero el código fuente.")
            return
        if not prefijos:
            messagebox.showwarning("Falta URL", "Escribe el prefijo de la URL.")
            return
        urls = extraer_urls(codigo, prefijos)
        self.txt_resultado.delete("1.0", "end")
        self.txt_resultado.insert("1.0", "\n".join(urls))
        self.lbl_estado.config(text=f"{len(urls)} URL(s) encontradas")

    def copiar(self):
        texto = self.txt_resultado.get("1.0", "end").strip()
        if texto:
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.lbl_estado.config(text="Copiado al portapapeles")

    def guardar(self):
        texto = self.txt_resultado.get("1.0", "end").strip()
        if not texto:
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(texto + "\n")
            self.lbl_estado.config(text="Archivo guardado")

    def limpiar(self):
        self.txt_codigo.delete("1.0", "end")
        self.txt_resultado.delete("1.0", "end")
        self.lbl_estado.config(text="")


if __name__ == "__main__":
    App().mainloop()