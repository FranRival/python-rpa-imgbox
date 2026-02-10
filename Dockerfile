FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema (Selenium + Chrome)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar TODO el proyecto
COPY . .

# Ejecutar cualquier script Python
ENTRYPOINT ["python", "crop.py"]
