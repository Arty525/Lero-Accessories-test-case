import asyncio
import os
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from django.conf import settings
from asgiref.sync import sync_to_async

# Инициализация Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from .models import Customer  # Импортируйте из вашего приложения


class DjangoBot:
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.setup_handlers()

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            """Обработчик команды /start с сохранением в модель Customer"""
            user = message.from_user

            # Используем sync_to_async для работы с Django ORM
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
                welcome_text = f"""
👋 С возвращением, {customer.first_name}!

✅ Вы уже зарегистрированы в системе как заказчик.
📞 Телефон: {customer.phone}
🏠 Адрес: {customer.address}

Выберите действие из меню ↓
                """

            except Customer.DoesNotExist:
                # Если пользователь новый
                welcome_text = """
👋 Добро пожаловать! 

Я бот для управления заказами. Для завершения регистрации мне нужна дополнительная информация.

📝 Пожалуйста, введите ваш номер телефона в формате:
+79991234567
                """

            await message.answer(welcome_text)

        @self.dp.message(F.text.regexp(r'^\+?[0-9]{10,15}$'))
        async def process_phone(message: types.Message):
            """Обработка номера телефона"""
            user = message.from_user
            phone = message.text.strip()

            try:
                # Проверяем, не занят ли телефон другим пользователем
                phone_exists = await sync_to_async(
                    lambda: Customer.objects.filter(phone=phone).exclude(telegram_id=str(user.id)).exists()
                )()

                if phone_exists:
                    await message.answer("❌ Этот номер телефона уже используется другим пользователем.")
                    return

                # Создаем или получаем пользователя
                customer, created = await sync_to_async(
                    lambda: Customer.objects.get_or_create(
                        telegram_id=str(user.id),
                        defaults={
                            'first_name': user.first_name or 'Неизвестно',
                            'last_name': user.last_name or 'Неизвестно',
                            'phone': phone,
                            'address': 'Не указан'
                        }
                    )
                )()

                if not created:
                    # Обновляем телефон если пользователь уже существует
                    customer.phone = phone
                    await sync_to_async(customer.save)()

                await message.answer(f"""
✅ Номер телефона сохранен: {phone}

Теперь введите ваш адрес:
(город, улица, дом, квартира)
                """)

            except Exception as e:
                await message.answer("❌ Ошибка при сохранении данных. Попробуйте еще раз.")

        @self.dp.message(F.text.len() > 10)
        async def process_address(message: types.Message):
            """Обработка адреса"""
            user = message.from_user
            address = message.text.strip()

            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
                customer.address = address
                await sync_to_async(customer.save)()

                await message.answer(f"""
🎉 Регистрация завершена!

📋 Ваши данные:
👤 Имя: {customer.first_name} {customer.last_name}
📞 Телефон: {customer.phone}
🏠 Адрес: {customer.address}

Теперь вы можете создавать заказы!
                """)

            except Customer.DoesNotExist:
                await message.answer("❌ Сначала введите номер телефона.")
            except Exception as e:
                await message.answer("❌ Ошибка при сохранении адреса.")

        @self.dp.message(Command("profile"))
        async def cmd_profile(message: types.Message):
            """Показать профиль заказчика"""
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(message.from_user.id))

                profile_info = f"""
📋 *Ваш профиль заказчика:*

👤 Имя: {customer.first_name} {customer.last_name}
📞 Телефон: `{customer.phone}`
🏠 Адрес: {customer.address}
🆔 Telegram ID: `{customer.telegram_id}`
                """

                await message.answer(profile_info, parse_mode="Markdown")

            except Customer.DoesNotExist:
                await message.answer("❌ Вы не зарегистрированы. Используйте /start")

    async def start_polling(self):
        """Запуск бота в режиме polling"""
        print("🤖 Telegram бот запущен с интеграцией модели Customer!")
        await self.dp.start_polling(self.bot)