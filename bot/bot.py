import asyncio
import os
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import Command
from aiogram.fsm import state
from aiogram.fsm.context import FSMContext
from django.conf import settings
from asgiref.sync import sync_to_async
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BotCommand, \
    WebAppInfo
from rest_framework.reverse import reverse_lazy, reverse
from .bot_utils import update_phone, update_address, get_profile, get_welcome_text, get_cart_data, add_item_in_cart, \
    remove_item, change_cart_item_quantity, new_order
from .models import Customer, Category, Product, Cart, CartItem, Order

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

class DjangoBot:
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.setup_handlers()


    def get_inline_menu(self):
        """Inline меню"""
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
            BotCommand(command="menu", description="Показать главное меню"),
        ]
        await self.bot.set_my_commands(commands)

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            """Обработчик команды /start с сохранением в модель Customer"""
            user = message.from_user
            welcome_text = await get_welcome_text(user)

            if welcome_text.startswith('С возвращением'):
                await message.answer(welcome_text, reply_markup=self.get_inline_menu())
            else:
                await message.answer(welcome_text)

        @self.dp.message(Command("menu"))
        async def cmd_menu(message: types.Message):
            """Показать главное меню"""
            menu_text = f"""
Выберите действие:
                """
            await message.answer(menu_text, reply_markup=self.get_inline_menu())

        @self.dp.message(F.text.regexp(r'^\+?[0-9]{10,15}$'))
        async def process_phone(message: types.Message):
            """Обработка номера телефона"""
            user = message.from_user
            phone = message.text.strip()
            answer_text = await update_phone(user, phone)
            await message.answer(answer_text)

        @self.dp.message(F.text.len() > 10)
        async def process_address(message: types.Message):
            """Обработка адреса"""
            user = message.from_user
            address = message.text.strip()
            answer_text = await update_address(user, address)
            await message.answer(answer_text)
            if answer_text.startswith("Регистрация завершена!"):
                await message.answer("Выберите действие:", reply_markup=self.get_inline_menu())
                await self.set_bot_commands()

        @self.dp.callback_query(F.data == "profile")
        async def cmd_profile(callback: types.CallbackQuery):
            """Показать профиль заказчика"""
            customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
            try:
                profile_info = await get_profile(customer)
                await callback.answer()
                await callback.message.answer(profile_info, parse_mode="Markdown")
            except Customer.DoesNotExist:
                await callback.answer()
                await callback.answer("❌ Вы не зарегистрированы. Используйте /start")

        @self.dp.callback_query(F.data == "categories")
        async def send_categories_list(callback: types.CallbackQuery):
            try:
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
                await callback.answer()
                await callback.message.answer("🗂️ Категории:", reply_markup=categories_menu)

            except Exception as e:
                print(f"Ошибка: {e}")
                await callback.answer()
                await callback.message.answer("❌ Ошибка загрузки категорий")

        @self.dp.callback_query(F.data.startswith("category_"))
        async def get_products_in_category(callback: types.CallbackQuery):
            try:
                category_id = callback.data.replace('category_', '')
                products = await sync_to_async(list)(
                    Product.objects.filter(category_id=category_id).values('id', 'title')
                )
                if not products:
                    await callback.message.answer("Товары в категории не найдены")
                    return

                products_buttons = []
                for product in products:
                    products_buttons.append([
                        InlineKeyboardButton(
                            text=product['title'],
                            callback_data='product_' + str(product['id'])
                        )
                    ])

                products_buttons.append([
                    InlineKeyboardButton(
                        text="⬅️ Назад к категориям",
                        callback_data="categories"
                    )
                ])
                products_menu = InlineKeyboardMarkup(inline_keyboard=products_buttons)
                await callback.answer()
                await callback.message.answer("📚 Товары:", reply_markup=products_menu)

            except Exception as e:
                print(f"Ошибка: {e}")
                await callback.answer()
                await callback.message.answer("❌ Ошибка загрузки товаров")

        @self.dp.callback_query(F.data.startswith("product_"))
        async def get_product_info(callback: types.CallbackQuery):
            try:
                product_id = callback.data.replace('product_', '')
                product = await sync_to_async(
                    Product.objects.get
                )(id=product_id)

                category_id = await sync_to_async(lambda: product.category.id)()

                product_menu = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='🛒 Добавить в корзину', callback_data=f'to_cart_{product.id}')],
                    [InlineKeyboardButton(text='⬅️ Назад к товарам', callback_data=f'category_{category_id}')]
                ])

                caption = f"""
📦 *{product.title}*
💰 Цена: {product.price} ₽
📝 {product.description or 'Описание отсутствует'}
                """

                if product.image:
                    try:
                        from aiogram.types import FSInputFile
                        photo = FSInputFile(product.image.path)
                        await callback.answer()
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
                    await callback.answer()
                    await callback.message.answer(
                        caption,
                        parse_mode="Markdown",
                        reply_markup=product_menu
                    )

            except Product.DoesNotExist:
                await callback.answer()
                await callback.message.answer("❌ Товар не найден")
            except Exception as e:
                print(f"Ошибка: {e}")
                await callback.answer()
                await callback.message.answer("❌ Ошибка загрузки информации о товаре")

        @self.dp.callback_query(F.data.startswith('to_cart_'))
        async def add_to_cart(callback: types.CallbackQuery):
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
                cart, created = await sync_to_async(Cart.objects.get_or_create)(customer=customer)

                product_id = callback.data.replace('to_cart_', '')
                message = await add_item_in_cart(cart, product_id)
                await callback.answer()
                await callback.message.answer(message)

            except Customer.DoesNotExist:
                await callback.message.answer('❌ Сначала зарегистрируйтесь с помощью /start')
            except Product.DoesNotExist:
                await callback.message.answer('❌ Товар не найден')
            except Exception as e:
                print(f'Ошибка: {e}')
                await callback.message.answer('❌ Ошибка при добавлении товара в корзину')

        @self.dp.callback_query(F.data == 'cart')
        async def get_cart(callback: types.CallbackQuery):
            try:
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
                cart_data, total_items, total_price = await get_cart_data(customer)
                await callback.message.answer('🛒 Ваша корзина:\n')
                for item in cart_data:
                    cart_item_menu = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text='✏️ Изменить количество', callback_data=f'change_quantity_{item['product__id']}')],
                        [InlineKeyboardButton(text='🗑️ Убрать из корзины', callback_data=f'remove_from_cart_{item['product__id']}')]
                    ])
                    await callback.message.answer(f"{item['product__title']} - "
f"{item['product__price']} ₽ | {item['quantity']} шт.\n", reply_markup=cart_item_menu, parse_mode="Markdown")
                total_text = f'Всего товаров: {total_items}, Сумма: {total_price}'

                cart_menu = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='🗑️ Очистить корзину',
                                          callback_data=f'clear_cart')],
                    [InlineKeyboardButton(text='📦 Оформить заказ',
                                          callback_data=f'take_order')]
                ])

                await callback.answer()
                await callback.message.answer(total_text, parse_mode="Markdown")
                await callback.message.answer('Выберите действие:', parse_mode="Markdown", reply_markup=cart_menu)
            except Cart.DoesNotExist:
                await callback.answer()
                await callback.message.answer('Корзина пуста')
            except Exception as e:
                print(f'Ошибка: {e}')
                await callback.answer()
                await callback.message.answer('❌ Ошибка при открытии корзины')

        @self.dp.callback_query(F.data.startswith('remove_from_cart_'))
        async def remove_cart_item(callback: types.CallbackQuery):
            customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
            item_id = callback.data.replace('remove_from_cart_', '')
            text_message = await remove_item(customer, item_id)
            await callback.message.answer(text_message, parse_mode="Markdown")
            await get_cart(callback)
            await callback.answer()

        @self.dp.callback_query(F.data.startswith('change_quantity_'))
        async def change_quantity(callback: types.CallbackQuery):
            item_id = callback.data.replace('change_quantity_', '')
            await callback.message.answer('Введите количество товара', parse='Markdown')
            @self.dp.message(F.text.isdigit())
            async def set_new_quantity(message: types.Message):
                quantity = message.text
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
                message_text = await change_cart_item_quantity(customer, item_id, quantity)
                await message.answer(message_text, parse_mode="Markdown")
                await get_cart(callback)
            await callback.answer()

        @self.dp.callback_query(F.data.startswith('take_order'))
        async def take_order(callback: types.CallbackQuery):
            try:
                print('take_order started')

                # Создаем клавиатуру с методами доставки
                delivery_method_list = []
                for delivery_method in Order.DELIVERY_METHOD_CHOICES:
                    delivery_method_list.append([
                        InlineKeyboardButton(
                            text=delivery_method[1],
                            callback_data=f"delivery_{delivery_method[0]}"
                        )
                    ])

                delivery_method_menu = InlineKeyboardMarkup(inline_keyboard=delivery_method_list)

                # Получаем данные пользователя
                customer = await sync_to_async(Customer.objects.get)(
                    telegram_id=str(callback.from_user.id)
                )
                cart = await sync_to_async(Cart.objects.get)(customer=customer)

                await callback.answer()
                await callback.message.answer(
                    'Выберите способ доставки:',
                    reply_markup=delivery_method_menu,
                    parse_mode="Markdown"
                )

            except Cart.DoesNotExist as e:
                print(f'⚠️ Ошибка: {e}')
                await callback.answer()
                await callback.message.answer('❌ Корзина пуста')
            except Customer.DoesNotExist as e:
                print(f'⚠️ Ошибка: {e}')
                await callback.answer()
                await callback.message.answer('❌ Сначала зарегистрируйтесь с помощью /start')
            except Exception as e:
                print(f'⚠️ Ошибка: {e}')
                await callback.answer()
                await callback.message.answer('❌ Ошибка при создании заказа')

        # Отдельный обработчик для выбора способа доставки
        @self.dp.callback_query(F.data.startswith('delivery_'))
        async def create_order(callback: types.CallbackQuery):
            try:
                print('create_order started')

                # Извлекаем метод доставки из callback_data
                delivery_method = callback.data.replace('delivery_', '')
                print(f'Delivery method: {delivery_method}')

                # Получаем данные пользователя
                customer = await sync_to_async(Customer.objects.get)(
                    telegram_id=str(callback.from_user.id)
                )
                cart = await sync_to_async(Cart.objects.get)(customer=customer)

                # Создаем заказ
                order_message = await new_order(customer, cart, delivery_method)

                await callback.answer()
                await callback.message.answer(order_message, parse_mode="Markdown")

            except Exception as e:
                print(f'⚠️ Ошибка в create_order: {e}')
                await callback.answer()
                await callback.message.answer('❌ Ошибка при создании заказа')

        @self.dp.callback_query(F.data.startswith('clear_cart'))
        async def clear_cart(callback: types.CallbackQuery):
            await callback.answer()
            await callback.message.answer('⚠️Вы уверены что хотите очистить корзину?', parse_mode="Markdown")
            clear_cart_menu = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='✅ Да',
                                      callback_data=f'yes')],
                [InlineKeyboardButton(text='❌ Нет',
                                      callback_data=f'no')]
            ])
            @self.dp.callback_query(F.data == 'yes')
            async def delete_cart(callback: types.CallbackQuery):
                customer = await sync_to_async(Customer.objects.get)(telegram_id=str(callback.from_user.id))
                cart = await sync_to_async(Cart.objects.get_or_create)(customer=customer)
                cart.delete()
                await callback.answer()
                await callback.message.answer('✅ Корзина очищена', parse_mode="Markdown")


    async def start_polling(self):
        """Запуск бота в режиме polling"""
        print("🤖 Telegram бот запущен")
        # Устанавливаем команды меню при запуске
        await self.set_bot_commands()
        await self.dp.start_polling(self.bot)