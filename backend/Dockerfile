# Koristimo laganu verziju Pythona (slim) da slika bude manja
FROM python:3.10-slim

# Postavljamo radni direktorijum unutar kontejnera
WORKDIR /app

# Instaliramo sistemske zavisnosti potrebne za kompajliranje nekih Python paketa
# (libpq-dev je potreban za Postgres drajver u nekim slucajevima, ali psycopg2-binary to uglavnom rjesava)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopiramo requirements fajl prvo (zbog keširanja Docker layera)
COPY requirements.txt .

# Instaliramo Python biblioteke
RUN pip install --no-cache-dir -r requirements.txt

# Kopiramo sav ostali kod u kontejner
COPY . .

# Otvaramo port 5000 za komunikaciju
EXPOSE 5000

# Komanda koja pokreće server
# Koristimo Gunicorn sa Eventlet workerom za najbolje performanse sa Socket.IO
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]