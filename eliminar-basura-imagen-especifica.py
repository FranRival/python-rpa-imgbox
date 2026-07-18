from pathlib import Path

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA_RAIZ = r"C:\Users\dell\Downloads\descarga\links5"

# Tamaño EXACTO del archivo en bytes
# Ejemplo: 15342
TAMANO_BYTES = 73989

# Extensiones a revisar (o deja vacío para revisar todo)
EXTENSIONES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# True = solo muestra lo que borraría
# False = elimina realmente
MODO_PRUEBA = True

# ==========================================

eliminados = 0
encontrados = 0

for archivo in Path(CARPETA_RAIZ).rglob("*"):

    if not archivo.is_file():
        continue

    if EXTENSIONES and archivo.suffix.lower() not in EXTENSIONES:
        continue

    if archivo.stat().st_size == TAMANO_BYTES:
        encontrados += 1

        if MODO_PRUEBA:
            print(f"[ENCONTRADO] {archivo}")
        else:
            archivo.unlink()
            eliminados += 1
            print(f"[ELIMINADO] {archivo}")

print("\n---------------------------")
print(f"Encontrados : {encontrados}")

if MODO_PRUEBA:
    print("Modo prueba: no se eliminó ningún archivo.")
else:
    print(f"Eliminados : {eliminados}")