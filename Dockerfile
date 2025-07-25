FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash oxossi
RUN chown -R oxossi:oxossi /app
USER oxossi

EXPOSE 8000

CMD ["python", "main.py"]