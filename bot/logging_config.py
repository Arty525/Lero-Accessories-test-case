# logging_config.py
import logging
import os
from datetime import datetime


def setup_logging():
    """Настройка логирования для приложения"""

    # Создаем папку для логов если ее нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Форматирование логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Базовый уровень логирования
    log_level = logging.INFO

    # Настройка root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )

    # Настройка для конкретных логгеров
    bot_logger = logging.getLogger('bot')
    bot_logger.setLevel(logging.INFO)

    # Логирование SQL запросов (для отладки)
    django_db_logger = logging.getLogger('django.db')
    django_db_logger.setLevel(logging.WARNING)