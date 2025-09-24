import random
import string
from datetime import datetime


async def order_number_generator() -> str:
    """
    Генерирует уникальный номер заказа в формате AB1234DMY
    где AB - случайные буквы, 1234 - случайное число, DMY - дата
    """
    # Генерация случайных букв (AB)
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))

    # Генерация случайного числа (1234)
    numbers = str(random.randint(1000, 9999))

    # Получение текущей даты (DMY)
    now = datetime.now()
    day = str(now.day).zfill(2)  # День с ведущим нулем
    month = str(now.month).zfill(2)  # Месяц с ведущим нулем
    year = str(now.year % 100).zfill(2)  # Последние 2 цифры года

    # Формирование полного номера
    order_number = f"{letters}{numbers}{day}{month}{year}"
    return order_number
