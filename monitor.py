import subprocess
from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime
from pathlib import Path

SCRIPTS_MONITOREADOS = [
    "uploader.py",
    "procesador.py",
    "Otro_script.py"
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
        output = subprocess.check_output(
            'wmic process where "name=\'python.exe\'" get CommandLine',
            shell=True
        ).decode()

        for script in SCRIPTS_MONITOREADOS:
            if script in output:
                return True

        return False

    except:
        return False

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {"date": str(datetime.now().date()), "minutes": 0}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def guardar_datos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


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

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=10)

        print("Enviado:", payload)
        print("Status:", response.status_code)

        return response.status_code == 200

    except Exception as e:
        print("Error enviando a API:", e)
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