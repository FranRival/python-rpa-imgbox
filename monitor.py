import subprocess
from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime
from pathlib import Path
import time

SCRIPTS_MONITOREADOS = [
    r"C:\Users\dell\Desktop\uploader\uploader.py",
    r"C:\Users\dell\Desktop\uploader\descargar.py",
    r"C:\Users\dell\Desktop\uploader\gallery-he\gallery.py",
]

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_URL = "https://api.emmanuelibarra.com/api/hours"
API_KEY = os.getenv("AUTOMATION_API_KEY")

if not API_KEY:
    raise ValueError("AUTOMATION_API_KEY no encontrada en .env")

DATA_FILE = BASE_DIR / "monitor_data.json"
INTERVAL_MINUTES = 10

# Ponlo en True para ver en consola las líneas de comando que PowerShell devuelve
DEBUG = False


def normalizar(texto):
    """Unifica formato: minúsculas, barras '\\' y sin comillas."""
    return texto.replace("/", "\\").replace('"', "").replace("'", "").lower()


OBJETIVOS = [normalizar(s) for s in SCRIPTS_MONITOREADOS]

PS_COMANDO = (
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "Get-CimInstance Win32_Process "
    "| Where-Object { $_.Name -like 'python*' } "
    "| ForEach-Object { $_.CommandLine }"
)


def algun_script_activo():
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_COMANDO],
            capture_output=True,
            timeout=30,
        )
        output = result.stdout.decode("utf-8", errors="ignore")

        lineas = [normalizar(l) for l in output.splitlines() if l.strip()]

        if DEBUG:
            print("--- Procesos Python detectados ---")
            for l in lineas:
                print(l)
            print("----------------------------------")

        for script in OBJETIVOS:
            if any(script in linea for linea in lineas):
                if DEBUG:
                    print("Detectado:", script)
                return True

        return False

    except Exception as e:
        print("Error detectando procesos:", e)
        return False


def datos_por_defecto():
    return {"date": str(datetime.now().date()), "minutes": 0}


def cargar_datos():
    default_data = datos_por_defecto()

    if not DATA_FILE.exists():
        return default_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print("⚠️ JSON vacío, reiniciando...")
            return default_data

        data = json.loads(content)

        # Validar estructura para evitar KeyError más adelante
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("date"), str)
            or not isinstance(data.get("minutes"), (int, float))
        ):
            print("⚠️ JSON con estructura inválida, reiniciando...")
            return default_data

        return data

    except json.JSONDecodeError:
        print("⚠️ JSON corrupto, reiniciando...")
        return default_data

    except Exception as e:
        print("Error leyendo JSON:", e)
        return default_data


def guardar_datos(data):
    # Escritura atómica: primero a un temporal y luego se reemplaza,
    # así un corte a mitad de escritura nunca deja el JSON corrupto.
    tmp = DATA_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        print("Error guardando JSON:", e)


def enviar_a_api(date, minutes):
    horas = round(minutes / 60, 2)

    payload = {"date": date, "hours": horas}
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

    intentos = 3
    for intento in range(intentos):
        try:
            with requests.Session() as session:  # cierra la conexión al terminar
                response = session.post(
                    API_URL, json=payload, headers=headers, timeout=10
                )

            print("Enviado:", payload)
            print("Status:", response.status_code)

            if 200 <= response.status_code < 300:
                return True

        except Exception as e:
            print(f"Error enviando a API (intento {intento + 1}):", e)

        # Esperar solo si todavía quedan intentos
        if intento < intentos - 1:
            time.sleep(30)

    return False


def main():
    hoy = str(datetime.now().date())
    data = cargar_datos()

    if data["date"] != hoy:
        if data["minutes"] > 0:
            if enviar_a_api(data["date"], data["minutes"]):
                data = {"date": hoy, "minutes": 0}
            else:
                print("No se reinicia contador por error en API")
        else:
            data = {"date": hoy, "minutes": 0}

    if algun_script_activo():
        data["minutes"] += INTERVAL_MINUTES
        print("Script activo. Minutos acumulados:", data["minutes"])
    else:
        print("Ningún script activo.")

    guardar_datos(data)


if __name__ == "__main__":
    main()


# ---------------- NOTAS (problemas observados en el servidor) ----------------
# - Se ejecuta cada 10 min = 144 requests/día. Si no se cierran, acumulan sockets.
# 27/11/26. FALSO: solo hace una peticion HTTP por dia. 1 request diario. 
# - Síntomas: SSH deja de responder, terminal de Lightsail falla, nginx sigue
#   corriendo, hace falta reboot.
# - Revisar: limits.conf (soft/hard nofile), workers de nginx
#   (cat /etc/nginx/nginx.conf | grep worker) y conexiones activas (ss -s).
# - 10-1-26: una semana sin enviar datos por problema de lectura del JSON
#   (cargar_datos / guardar_datos).

    #problemas... cada 10 minutos se ejecuta. en total son 144 request al dia. Si algunas no se cierran, acumulan sockets.

    #Conexiones HTTP quedan abiertas

    #SSH deja de responder
    #terminal lightsail fallando
    #nginx sigue running
    #necesita un reboot

    #Este programa corre con Python, y Gunicorn crea problemas

    #Cada request crea un Worker
    #el worker no se libera
    #Aculumacion de horas + dias hace que el servidor llegue al limite en silencio....

    #Acumulacion de fallas hace que falle:

    #Sockets
    #SSH
    #nginx

    ##Agregamoslimites en limits.conf - soft nofile 65.. y hard nofile 65...

    #cat /etc/nginx/nginx.conf | grep worker - da el numero total de workers - y cada worker abre conexiones imultaneas

    #ss -s - cantidad de conexiones activas. X can be applied inmmediately. ahi es donde vemos si hay saturacion



#---10-1-26 --- desde hace una semana no estaba enviando datos a la API - es un problema de lectura del JSON. Cargar_datos y guardar_datos tienen la vulnerabilidad. 