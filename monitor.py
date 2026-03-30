import subprocess
from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime
from pathlib import Path
import time

SCRIPTS_MONITOREADOS = [
    "uploader.py",
    "descargar.py"
]

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_URL = "https://api.emmanuelibarra.com/api/hours"

API_KEY = os.getenv('AUTOMATION_API_KEY')

if not API_KEY:
    raise ValueError('AUTOMATION_API_KEY no encontrada en .env')

DATA_FILE = BASE_DIR / "monitor_data.json"
INTERVAL_MINUTES = 10


def algun_script_activo():
    try:
        cmd = 'powershell "Get-CimInstance Win32_Process | Where-Object {$_.Name -like \'python*\'} | Select-Object CommandLine"'
        output = subprocess.check_output(cmd, shell=True).decode()

        for script in SCRIPTS_MONITOREADOS:
            if script.lower() in output.lower():
                return True

        return False

    except Exception as e:
        print("Error detectando procesos:", e)
        return False

def cargar_datos():
    default_data = {
        "date": str(datetime.now().date()),
        "minutes": 0
    }

    if not os.path.exists(DATA_FILE):
        return default_data

    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()

            if not content:
                print("⚠️ JSON vacío, reiniciando...")
                return default_data

            return json.loads(content)

    except json.JSONDecodeError:
        print("⚠️ JSON corrupto, reiniciando...")
        return default_data

    except Exception as e:
        print("Error leyendo JSON:", e)
        return default_data


def guardar_datos(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Error guardando JSON:", e)


def enviar_a_api(date, minutes):
    horas = round(minutes / 60, 2)

    payload = {
        "date": date,
        "hours": horas
    }

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    for intento in range(3):
        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=10)

            print("Enviado:", payload)
            print("Status:", response.status_code)

            if response.status_code == 200:
                return True

        except Exception as e:
            print(f"Error enviando a API (intento {intento+1}):", e)

        # 🔴 esperar antes de intentar otra vez
        time.sleep(30)

    return False

def main():
    hoy = str(datetime.now().date())
    data = cargar_datos()

    if data["date"] != hoy:
        if data["minutes"] > 0:
            enviado = enviar_a_api(data["date"], data["minutes"])
            if enviado:
                data = {"date": hoy, "minutes": 0}
            else:
                print("No se reinicia contador por error en API")
        else:
            data = {"date": hoy, "minutes": 0}

    # Si uploader está activo → sumar minutos
    if algun_script_activo():
        data["minutes"] += INTERVAL_MINUTES
        print("Uploader activo. Minutos acumulados:", data["minutes"])
    else:
        print("Uploader NO activo.")

    guardar_datos(data)


if __name__ == "__main__":
    main()



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