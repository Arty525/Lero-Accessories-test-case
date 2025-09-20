FROM python:3.13-slim

# Установка только необходимых зависимостей
RUN apt-get update && apt-get install -y \
    python3.13 \
    gcc \
    python3-dev \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала копируем только requirements.txt
COPY requirements.txt .

# Установка зависимостей с обработкой платформо-специфичных пакетов
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]

EXPOSE 8000