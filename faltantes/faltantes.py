import os
import sys
import shutil

def main():
    if len(sys.argv) != 2:
        print(r"Uso: python faltantes.py <C:\Users\dell\Desktop\listo\132\faltantes.txt>")
        return

    txt_path = sys.argv[1]

    if not os.path.isfile(txt_path):
        print("El archivo faltantes.txt no existe.")
        return

    base_dir = os.path.dirname(os.path.abspath(txt_path))
    destino = os.path.join(base_dir, "Faltantes")

    os.makedirs(destino, exist_ok=True)

    with open(txt_path, "r", encoding="utf-8") as f:
        nombres_validos = set(line.strip() for line in f if line.strip())

    print("Carpetas listadas en faltantes.txt:")
    print(nombres_validos)
    print("-" * 50)

    for item in os.listdir(base_dir):
        ruta_item = os.path.join(base_dir, item)

        if os.path.isdir(ruta_item) and item != "Faltantes":
            if item not in nombres_validos:
                destino_final = os.path.join(destino, item)

                if os.path.exists(destino_final):
                    print(f"Ya existe en destino, omitiendo: {item}")
                else:
                    print(f"Moviendo carpeta NO listada: {item}")
                    shutil.move(ruta_item, destino_final)
            else:
                print(f"OK (está en lista): {item}")

    print("\nProceso terminado.")

if __name__ == "__main__":
    main()