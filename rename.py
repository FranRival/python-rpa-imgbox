import os
import sys

# ── Configuración ──────────────────────────────────────────────────
DIRECTORIO   = r"C:\Users\dell\Downloads\descarga1\links35"        # Carpeta donde están las subcarpetas a renombrar
NOMBRE_BASE  = "Whore name "     # Prefijo fijo
NUMERO_INICIO = 3033       # Número inicial
INCREMENTO   = 1          # Cuánto sube cada vez
# ───────────────────────────────────────────────────────────────────


def obtener_carpetas(directorio):
    """Devuelve las subcarpetas ordenadas alfabéticamente."""
    entradas = os.scandir(directorio)
    carpetas = sorted(
        [e for e in entradas if e.is_dir()],
        key=lambda e: e.name
    )
    return carpetas


def main():
    directorio = os.path.abspath(DIRECTORIO)

    if not os.path.isdir(directorio):
        print(f"[ERROR] No se encontró el directorio: {directorio}")
        sys.exit(1)

    carpetas = obtener_carpetas(directorio)

    if not carpetas:
        print("[INFO] No se encontraron subcarpetas en el directorio.")
        sys.exit(0)

    # -- Construir el plan de renombrado --------------------------------
    plan = []
    numero = NUMERO_INICIO
    for carpeta in carpetas:
        nombre_nuevo = f"{NOMBRE_BASE} {numero}"
        ruta_vieja   = carpeta.path
        ruta_nueva   = os.path.join(directorio, nombre_nuevo)
        plan.append((ruta_vieja, ruta_nueva, carpeta.name, nombre_nuevo))
        numero += INCREMENTO

    # -- Mostrar resumen (dry-run) ---------------------------------------
    print(f"\nDirectorio: {directorio}")
    print(f"Carpetas encontradas: {len(plan)}\n")
    print(f"{'NOMBRE ACTUAL':<40}  →  NOMBRE NUEVO")
    print("-" * 70)
    for ruta_vieja, ruta_nueva, viejo, nuevo in plan:
        estado = ""
        if os.path.exists(ruta_nueva) and ruta_vieja != ruta_nueva:
            estado = "  ⚠ ya existe, se omitirá"
        print(f"  {viejo:<38}  →  {nuevo}{estado}")

    # -- Confirmación ---------------------------------------------------
    print("\n¿Confirmas el renombrado? (s/n): ", end="")
    respuesta = input().strip().lower()
    if respuesta not in ("s", "si", "sí", "y", "yes"):
        print("\nOperación cancelada. No se renombró ninguna carpeta.")
        sys.exit(0)

    # -- Ejecutar renombrado --------------------------------------------
    renombradas = 0
    omitidas    = 0
    errores     = 0

    for ruta_vieja, ruta_nueva, viejo, nuevo in plan:
        if ruta_vieja == ruta_nueva:
            print(f"  [=] Sin cambio:  {viejo}")
            omitidas += 1
            continue
        if os.path.exists(ruta_nueva):
            print(f"  [!] Omitida (ya existe destino):  {viejo}  →  {nuevo}")
            omitidas += 1
            continue
        try:
            os.rename(ruta_vieja, ruta_nueva)
            print(f"  [✓] Renombrada:  {viejo}  →  {nuevo}")
            renombradas += 1
        except Exception as e:
            print(f"  [✗] Error al renombrar '{viejo}': {e}")
            errores += 1

    # -- Resumen final --------------------------------------------------
    print(f"\n── Resultado ──────────────────────────────")
    print(f"  Renombradas: {renombradas}")
    print(f"  Omitidas:    {omitidas}")
    print(f"  Errores:     {errores}")
    print(f"───────────────────────────────────────────\n")


if __name__ == "__main__":
    main()