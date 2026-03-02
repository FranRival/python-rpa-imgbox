import subprocess
from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime

load_dotenv()

API_URL = "https://api.emmanuelibarra.com/api/hours"
API_KEY = "TU_API_KEY_REAL"

API_KEY = os.getenv('AUTOMATION_API_KEY')

if not API_KEY:
    raise ValueError('AUTOMATION_API_KEY no encontrada en .env')

DATA_FILE = "monitor_data.json"
INTERVAL_MINUTES = 10


def uploader_activo():
    try:
        output = subprocess.check_output("tasklist", shell=True).decode()
        return "Uploader.py" in output
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

    response = requests.post(API_URL, json=payload, headers=headers, timeout=10)

    print("Enviado:", payload)
    print("Status:", response.status_code)


def main():
    hoy = str(datetime.now().date())
    data = cargar_datos()

    # Si cambió el día → enviar datos del día anterior
    if data["date"] != hoy:
        if data["minutes"] > 0:
            enviar_a_api(data["date"], data["minutes"])

        # Reiniciar contador para nuevo día
        data = {"date": hoy, "minutes": 0}

    # Si uploader está activo → sumar minutos
    if uploader_activo():
        data["minutes"] += INTERVAL_MINUTES
        print("Uploader activo. Minutos acumulados:", data["minutes"])
    else:
        print("Uploader NO activo.")

    guardar_datos(data)


if __name__ == "__main__":
    main()