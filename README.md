# Telegram Bot for Order Management

Бот для управления заказами с интеграцией Django и PostgreSQL.

## 🚀 Функциональность

### Для клиентов:
- 📋 Регистрация и профиль
- 🛍️ Просмотр категорий и товаров
- 🛒 Корзина с управлением количеством
- 📦 Оформление заказов
- 📊 История заказов

### Администрирование
Администрирование производится из стандартной админ-панели Django

## 🛠️ Установка и запуск

### Предварительные требования
- Python 3.8+
- PostgreSQL
- Docker и Docker Compose (опционально)

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd telegram-bot
```

### 2. Настройка виртуального окружения

    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    venv\Scripts\activate     # Windows

### 3. Установка зависимостей

    pip install -r requirements.txt

### 4. Настройка базы данных
Создайте файл .env в корневой директории проекта

```Содержимое .env
DB_NAME=telegram_bot
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
TG_BOT_TOKEN=your_telegram_bot_token
TG_WEBHOOK_URL=your_webhook_url
```

### 5. Выполните миграции

    python manage.py makemigrations
    python manage.py migrate

### 6. Создайте суперпользователя

    python manage.py createsuperuser

### Запуск Docker

    docker-compose up --build

### Запуск тестов

    python -m pytest tests.py -v

### Запуск тестов с покрытием

    python -m pytest tests.py --cov=bot --cov-report=html

### Запуск тестов конкретного модуля

    python -m pytest tests.py::TestBotUtils -v

## Список тестов

### Модуль bot_utils
✅ Приветственный текст для различных типов пользователей

✅ Обновление телефона и адреса

✅ Обработка ошибок регистрации

✅ Работа с корзиной (добавление/удаление/изменение)

✅ Создание заказов

### Модуль services
✅ Генерация номеров заказов

✅ Обработка ошибок генерации

### Модуль views
✅ Обработка вебхуков Telegram

✅ Обработка невалидных запросов

✅ Обработка исключений

### 🐛 Обработка ошибок
Приложение включает комплексную обработку ошибок:

#### Уровни логирования:
INFO: Основные операции (регистрация, заказы)

WARNING: Предупреждения (повторные попытки, нестандартные ситуации)

ERROR: Критические ошибки (ошибки БД, сетевые проблемы)

#### Типы обрабатываемых ошибок:
Ошибки базы данных

Сетевые ошибки

Ошибки валидации данных

Ошибки Telegram API

## 📊 Логирование
Логи сохраняются в папке logs/ с ежедневной ротацией:

bot_YYYYMMDD.log - основные логи приложения

Консольный вывод в реальном времени

Пример лога:
    
    2024-01-15 10:30:00 - bot.bot_utils - INFO - Получение приветственного текста для пользователя 123456
    2024-01-15 10:30:01 - bot.bot_utils - INFO - Пользователь 123456 найден как заказчик
    2024-01-15 10:30:02 - bot.services - INFO - Сгенерирован номер заказа: AB1234150124

# Структура проекта

telegram-bot/
├── bot/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── bot.py              # Основная логика бота
│   ├── bot_utils.py        # Вспомогательные функции
│   ├── logging_config.py   # Настройки логирования
│   ├── models.py           # Модели данных
│   ├── services.py         # Сервисные функции
│   ├── tests.py            # Тесты
│   ├── urls.py             # URL маршруты
│   └── views.py            # Обработчики вебхуков
├── logs/                   # Логи приложения
├── media/                  # Медиафайлы
├── .env               # Переменные окружения
├── docker-compose.yml # Docker конфигурация
├── Dockerfile
├── manage.py          # Django management
└── requirements.txt   # Зависимости

