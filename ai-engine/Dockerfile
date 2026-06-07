FROM python:3.11-slim

WORKDIR /app

# Sistema — dependencias de Prophet (Stan) y psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El contenedor no sirve HTTP; se usa como job batch.
# El script a ejecutar se pasa como CMD en docker-compose o CI.
CMD ["python", "train_prophet.py"]
