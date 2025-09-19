import asyncio
import os
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import Command
from django.conf import settings
from asgiref.sync import sync_to_async
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BotCommand, \
    WebAppInfo
from rest_framework.reverse import reverse_lazy, reverse

# Инициализация Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from .models import Customer, Category, Product, Cart, CartItem  # Импортируйте из вашего приложения


class DjangoBot:
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.setup_handlers()


    def get_inline_menu(self):
        """Inline меню для дополнительных действий"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders")],
                [InlineKeyboardButton(text='🗒️ Категории товаров', callback_data="categories")],
            ]
        )

    async def set_bot_commands(self):
        """Установка команд меню бота"""
        commands = [
            BotCommand(command="start", description="Запустить бота"),
        ]
        await self.bot.set_my_commands(commands)

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

                # Показываем дополнительное inline меню
                await message.answer("Дополнительные опции:", reply_markup=self.get_inline_menu())

            except Customer.DoesNotExist:
                # Если пользователь новый
                welcome_text = """
👋 Добро пожаловать! 

Я бот для управления заказами. Для завершения регистрации мне нужна дополнительная информация.

📝 Пожалуйста, введите ваш номер телефона в формате:
+79991234567
                """
                await message.answer(welcome_text)

        @self.dp.message(Command("menu"))
        async def cmd_menu(message: types.Message):
            """Показать главное меню"""
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(message.from_user.id))
                menu_text = f"""
📱 Главное меню, {customer.first_name}!

Выберите действие:
                """
                await message.answer("Дополнительные опции:", reply_markup=self.get_inline_menu())

            except Customer.DoesNotExist:
                await message.answer("❌ Сначала завершите регистрацию через /start")

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

                # После завершения регистрации показываем меню
                success_text = f"""
🎉 Регистрация завершена!

📋 Ваши данные:
👤 Имя: {customer.first_name} {customer.last_name}
📞 Телефон: {customer.phone}
🏠 Адрес: {customer.address}

Теперь вы можете создавать заказы!
                """
                await message.answer("Выберите действие:", reply_markup=self.get_inline_menu())

                # Устанавливаем команды меню
                await self.set_bot_commands()

            except Customer.DoesNotExist:
                await message.answer("❌ Сначала введите номер телефона.")
            except Exception as e:
                await message.answer("❌ Ошибка при сохранении адреса.")

        # Обработчики inline кнопок
        @self.dp.callback_query(F.data == "profile")
        async def cmd_profile(callback: types.CallbackQuery):
            """Показать профиль заказчика"""
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))

                profile_info = f"""
        📋 *Ваш профиль заказчика:*

        👤 Имя: {customer.first_name} {customer.last_name}
        📞 Телефон: `{customer.phone}`
        🏠 Адрес: {customer.address}
        🆔 Telegram ID: `{customer.telegram_id}`
                        """

                await callback.message.answer(profile_info, parse_mode="Markdown")

            except Customer.DoesNotExist:
                await callback.answer("❌ Вы не зарегистрированы. Используйте /start")

        @self.dp.callback_query(F.data == "categories")
        async def send_categories_list(callback: types.CallbackQuery):
            """Получить категории через API и отправить списком"""
            try:
                # Получаем категории и преобразуем в список
                categories = await sync_to_async(list)(Category.objects.all())

                if not categories:
                    await callback.message.answer("📭 Категории не найдены")
                    await callback.answer()
                    return

                categories_buttons = []
                for category in categories:
                    categories_buttons.append([
                        InlineKeyboardButton(
                            text=category.title,
                            callback_data='category_' + str(category.id)
                        )
                    ])

                categories_menu = InlineKeyboardMarkup(inline_keyboard=categories_buttons)

                await callback.message.answer("🗂️ Категории:", reply_markup=categories_menu)
                await callback.answer("✅ Категории загружены")

            except Exception as e:
                print(f"Ошибка: {e}")
                await callback.message.answer("❌ Ошибка загрузки категорий")
                await callback.answer("⚠️ Произошла ошибка")

        from asgiref.sync import sync_to_async

        # Обработчик для категорий
        @self.dp.callback_query(F.data.startswith("category_"))
        async def get_products_in_category(callback: types.CallbackQuery):
            print('get_products_in_category')
            try:
                category_id = callback.data.replace('category_', '')

                # Получаем товары из категории с sync_to_async
                products = await sync_to_async(list)(
                    Product.objects.filter(category_id=category_id).values('id', 'title')
                )

                if not products:
                    await callback.message.answer("Товары в категории не найдены")
                    await callback.answer()
                    return

                products_buttons = []
                for product in products:
                    products_buttons.append([
                        InlineKeyboardButton(
                            text=product['title'],
                            callback_data='product_' + str(product['id'])
                        )
                    ])

                # Добавляем кнопку "Назад"
                products_buttons.append([
                    InlineKeyboardButton(
                        text="⬅️ Назад к категориям",
                        callback_data="categories"
                    )
                ])

                products_menu = InlineKeyboardMarkup(inline_keyboard=products_buttons)

                await callback.message.answer("📚 Товары:", reply_markup=products_menu)
                await callback.answer("✅ Товары загружены")

            except Exception as e:
                print(f"Ошибка: {e}")
                await callback.message.answer("❌ Ошибка загрузки товаров")
                await callback.answer()

        # Обработчик для товаров
        @self.dp.callback_query(F.data.startswith("product_"))
        async def get_product_info(callback: types.CallbackQuery):
            print('get_product_info')
            try:
                product_id = callback.data.replace('product_', '')

                # Получаем товар с sync_to_async
                product = await sync_to_async(
                    Product.objects.get
                )(id=product_id)

                # Создаем меню с sync_to_async для получения категории
                category_id = await sync_to_async(lambda: product.category.id)()

                product_menu = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='🛒 Добавить в корзину', callback_data=f'to_cart_{product.id}')],
                    [InlineKeyboardButton(text='⬅️ Назад к товарам', callback_data=f'category_{category_id}')]
                ])

                # Формируем caption
                caption = f"""
📦 *{product.title}*
💰 Цена: {product.price} ₽
📝 {product.description or 'Описание отсутствует'}
                """

                # Отправляем фото если есть
                if product.image:
                    try:
                        from aiogram.types import FSInputFile
                        photo = FSInputFile(product.image.path)
                        await callback.message.answer_photo(
                            photo=photo,
                            caption=caption,
                            parse_mode="Markdown",
                            reply_markup=product_menu
                        )
                    except Exception as e:
                        print(f"Ошибка загрузки изображения: {e}")
                        await callback.message.answer(
                            caption,
                            parse_mode="Markdown",
                            reply_markup=product_menu
                        )
                else:
                    await callback.message.answer(
                        caption,
                        parse_mode="Markdown",
                        reply_markup=product_menu
                    )

                await callback.answer()

            except Product.DoesNotExist:
                await callback.message.answer("❌ Товар не найден")
                await callback.answer()
            except Exception as e:
                print(f"Ошибка: {e}")
                await callback.message.answer("❌ Ошибка загрузки информации о товаре")
                await callback.answer()

        #добавление товара в корзину
        @self.dp.callback_query(F.data.startswith('to_cart_'))
        async def add_to_cart(callback: types.CallbackQuery):
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
                cart, created = await sync_to_async(Cart.objects.get_or_create)(customer=customer)

                product_id = callback.data.replace('to_cart_', '')
                product = await sync_to_async(Product.objects.get)(id=product_id)

                # ПРАВИЛЬНО: Проверяем и получаем cart_item за один запрос
                cart_item_exists = await sync_to_async(
                    lambda: CartItem.objects.filter(cart=cart, product=product).exists()
                )()

                if cart_item_exists:
                    # Если товар уже есть, обновляем количество
                    cart_item = await sync_to_async(
                        CartItem.objects.get
                    )(cart=cart, product=product)
                    cart_item.quantity += 1
                    await sync_to_async(cart_item.save)()
                    message = f"✅ Добавлена еще 1 шт. товара \"{product.title}\""
                else:
                    # Если товара нет, создаем новую запись
                    cart_item = await sync_to_async(
                        CartItem.objects.create
                    )(cart=cart, product=product, quantity=1)
                    message = f"✅ Товар \"{product.title}\" добавлен в корзину"

                await callback.message.answer(message)
                await callback.answer()

            except Customer.DoesNotExist:
                await callback.message.answer('❌ Сначала зарегистрируйтесь с помощью /start')
                await callback.answer()
            except Product.DoesNotExist:
                await callback.message.answer('❌ Товар не найден')
                await callback.answer()
            except Exception as e:
                print(f'Ошибка: {e}')
                await callback.message.answer('❌ Ошибка при добавлении товара в корзину')
                await callback.answer()

        @self.dp.callback_query(F.data == 'cart')
        async def get_cart(callback: types.CallbackQuery):
            print('get_cart')
            try:
                print('get customer')
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
                print('get cart')
                cart = await sync_to_async(Cart.objects.get)(customer=customer)
                print('get cart items')
                cart_items = await sync_to_async(CartItem.objects.filter)(cart=cart)

                print('create text')
                products_text = 'Список товаров в корзине:\n\n'

                # Один асинхронный запрос для всех данных
                cart_data = await sync_to_async(
                    lambda: list(cart.items.select_related('product').values(
                        'product__title', 'product__price', 'quantity'
                    ))
                )()

                for item in cart_data:
                    print('add item into text')
                    products_text += f"{item['product__title']} - {item['product__price']} ₽ | {item['quantity']} шт.\n"

                print('total text')
                # Асинхронно получаем общие данные
                total_items = await sync_to_async(lambda: cart.total_items)()
                total_price = await sync_to_async(lambda: cart.total_price)()

                products_text += f'Всего товаров: {total_items}\nИтого: {total_price} ₽'

                await callback.message.answer(products_text, parse_mode="Markdown")
                await callback.answer()

            except Cart.DoesNotExist:
                await callback.message.answer('Корзина пуста')

            except Exception as e:
                print(f'Ошибка: {e}')
                await callback.message.answer('❌ Ошибка при открытии корзины')
                await callback.answer()

# @self.dp.callback_query(F.data == "feedback")
# async def feedback_callback(callback: types.CallbackQuery):
#     await callback.message.answer("⭐ Пожалуйста, оставьте ваш отзыв здесь: https://forms.gle/example")
#     await callback.answer()
#
# @self.dp.callback_query(F.data == "news")
# async def news_callback(callback: types.CallbackQuery):
#     await callback.message.answer("📢 Подпишитесь на наши новости: @lero_news")
#     await callback.answer()

    async def start_polling(self):
        """Запуск бота в режиме polling"""
        print("🤖 Telegram бот запущен с интеграцией модели Customer!")
        # Устанавливаем команды меню при запуске
        await self.set_bot_commands()
        await self.dp.start_polling(self.bot)