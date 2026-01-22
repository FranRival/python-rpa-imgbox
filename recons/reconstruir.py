import pandas as pd
from pathlib import Path

archivo = "datos.xlsx"
salida  = "resultado.xlsx"

if not Path(archivo).exists():
    print("❌ No existe datos.xlsx en la carpeta.")
    exit()

print("📖 Leyendo Excel...")
df = pd.read_excel(archivo, header=None)

# Columnas:
COL_HTML = 0   # A
COL_NOMBRE = 1 # B
COL_OBJETIVO = 2 # C

# Limpiamos datos
df["nombre"] = df[COL_NOMBRE].astype(str).str.strip()
df["nombre_norm"] = df["nombre"].str.lower()

objetivo = df[COL_OBJETIVO].dropna().astype(str).str.strip()
objetivo_norm = objetivo.str.lower()

# Creamos mapa nombre -> html (A)
mapa = {}
for _, row in df.iterrows():
    nombre = row["nombre_norm"]
    html = row[COL_HTML]

    if nombre and nombre not in mapa:
        mapa[nombre] = html

print("🔗 Reconstruyendo orden correcto...")
resultado = []
encontrados = 0
faltantes = []

for nombre, nombre_norm in zip(objetivo, objetivo_norm):
    html = mapa.get(nombre_norm)

    if html is not None:
        encontrados += 1
    else:
        faltantes.append(nombre)

    resultado.append({
        "carpeta": nombre,
        "html": html
    })

print(f"✅ Encontrados: {encontrados} / {len(objetivo)}")

if faltantes:
    print("⚠️ No encontrados:")
    for f in faltantes[:10]:
        print("   -", f)
    if len(faltantes) > 10:
        print("   ...")

# Exportar
df_out = pd.DataFrame(resultado)
df_out.to_excel(salida, index=False)

print("💾 Archivo generado:", salida)
