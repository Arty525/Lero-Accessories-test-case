import os
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from django.conf import settings
from asgiref.sync import sync_to_async
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from .bot_utils import update_phone, update_address, get_profile, get_welcome_text, get_cart_data, add_item_in_cart, \
    remove_item, change_cart_item_quantity, new_order
from .models import Customer, Category, Product, Cart, Order, Manager
from .middlewares import ManagerMiddleware

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

    def get_admin_keyboard(self):
        """Клавиатура администратора"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📦 Управление заказами"), KeyboardButton(text="🛍️ Управление товарами")],
                [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Менеджеры")],
                [KeyboardButton(text="🔙 Выйти из админки")]
            ],
            resize_keyboard=True
        )


    async def set_bot_commands(self):
        """Установка команд меню бота"""
        commands = [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="menu", description="Показать главное меню"),
        ]
        await self.bot.set_my_commands(commands)

    async def is_manager(self, user_id):
        """Проверяет, является ли пользователь менеджером"""
        try:
            manager = await sync_to_async(Manager.objects.get)(telegram_id=user_id)
            return manager.is_staff
        except Manager.DoesNotExist:
            return False

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
                        [InlineKeyboardButton(text='✏️ Изменить количество',
                                              callback_data=f'change_quantity_{item['product__id']}')],
                        [InlineKeyboardButton(text='🗑️ Убрать из корзины',
                                              callback_data=f'remove_from_cart_{item['product__id']}')]
                    ])
                    await callback.message.answer(f"{item['product__title']} - "
                                                  f"{item['product__price']} ₽ | {item['quantity']} шт.\n",
                                                  reply_markup=cart_item_menu, parse_mode="Markdown")
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
                # Извлекаем метод доставки из callback_data
                delivery_method = callback.data.replace('delivery_', '')

                # Получаем данные пользователя
                customer = await sync_to_async(Customer.objects.get)(
                    telegram_id=str(callback.from_user.id)
                )
                cart = await sync_to_async(Cart.objects.get)(customer=customer)

                order_message = await new_order(customer, cart, delivery_method)
                await callback.answer()
                await callback.message.answer('Подтвердите заказ:', parse_mode="Markdown")
                order_menu = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='✅ Подтвердить',
                                          callback_data='confirm')],
                    [InlineKeyboardButton(text='❌ Отмена',
                                          callback_data='cancel')]
                ])
                await callback.answer()
                await callback.message.answer(order_message, reply_markup=order_menu, parse_mode="Markdown")

                @self.dp.callback_query(F.data == 'confirm')
                async def confirm(callback: types.CallbackQuery):
                    order = await sync_to_async(Order.objects.filter)(customer=customer)
                    order = await sync_to_async(order.latest)('order_date_time')
                    order.is_confirmed = True
                    await sync_to_async(order.save)()
                    await sync_to_async(cart.items.all().delete)()
                    await callback.answer()
                    await callback.message.answer('✅ Заказ подтвержден', parse_mode="Markdown")

                @self.dp.callback_query(F.data == 'cancel')
                async def cancel(callback: types.CallbackQuery):
                    order = await sync_to_async(Order.objects.filter)(customer=customer)
                    order = await sync_to_async(order.latest)('order_date_time')
                    order.status = 'cancelled'
                    await callback.answer()
                    await callback.message.answer('❌ Заказ отменен', parse_mode="Markdown")

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

        @self.dp.callback_query(F.data == 'orders')
        async def show_orders(callback: types.CallbackQuery):
            try:
                customer = await sync_to_async(Customer.objects.get)(
                    telegram_id=str(callback.from_user.id)
                )

                # Получаем заказы с предзагрузкой связанных данных
                orders = await sync_to_async(list)(
                    Order.objects.filter(customer=customer)
                    .select_related('customer')
                    .prefetch_related('items__product')
                    .order_by('-order_date_time')
                )

                if not orders:
                    await callback.message.answer("📭 У вас пока нет заказов")
                    await callback.answer()
                    return

                for order in orders:
                    # Все данные уже загружены, можно обращаться к свойствам
                    delivery_method = await sync_to_async(order.get_delivery_method_display)()
                    status = await sync_to_async(order.get_order_status)()

                    order_menu = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text='❌ Отменить заказ',
                            callback_data=f'cancel_{order.id}'
                        )],
                    ])

                    order_info = f"""
        📦 *Заказ №{order.order_number}*

        🏠 Адрес: {order.address}
        🚚 Способ доставки: {delivery_method}
        🛍️ Товаров: {order.total_items} шт.
        💰 Сумма: {order.total_price} ₽
        🛃 Статус: {status}
                    """
                    if order.is_confirmed and order.status != 'cancelled':
                        await callback.message.answer(order_info, reply_markup=order_menu, parse_mode="Markdown")
                    else:
                        await callback.message.answer(order_info, parse_mode="Markdown")

                await callback.answer()

            except Customer.DoesNotExist:
                await callback.message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
                await callback.answer()
            except Exception as e:
                print(f"Ошибка при загрузке заказов: {e}")
                await callback.message.answer("❌ Ошибка при загрузке заказов")
                await callback.answer()

            @self.dp.callback_query(F.data.startswith('cancel_'))
            async def cancel(callback: types.CallbackQuery):
                order_id = callback.data.replace('cancel_', '')
                order = await sync_to_async(Order.objects.get)(id=order_id)
                order.status = 'cancelled'
                await sync_to_async(order.save)()
                await callback.answer()
                await callback.message.answer('❌ Заказ отменен', parse_mode="Markdown")

        # АДМИНИСТРАТИВНЫЕ КОМАНДЫ
        @self.dp.message(Command("admin"))
        async def admin_login(message: types.Message):
            """Вход в административную панель"""
            user_id = str(message.from_user.id)

            is_admin = await self.is_manager(user_id)
            if not is_admin:
                await message.answer("❌ У вас нет доступа к административной панели")
                return

            await message.answer(
                "👋 Добро пожаловать в панель администратора!",
                reply_markup=self.get_admin_keyboard()
            )

        @self.dp.message(F.text == "🔙 Выйти из админки")
        async def admin_logout(message: types.Message):
            """Выход из административной панели"""
            await message.answer(
                "Вы вышли из административной панели",
                reply_markup=ReplyKeyboardRemove()
            )

        @self.dp.message(F.text == "📦 Управление заказами")
        async def admin_orders_management(message: types.Message):
            """Управление заказами"""
            is_admin = await self.is_manager(str(message.from_user.id))
            if not is_admin:
                await message.answer("❌ У вас нет прав")
                return

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_orders_all")],
                    [InlineKeyboardButton(text="⏳ В обработке", callback_data="admin_orders_pending")],
                    [InlineKeyboardButton(text="🚚 В доставке", callback_data="admin_orders_delivery")],
                    [InlineKeyboardButton(text="✅ Завершенные", callback_data="admin_orders_completed")]
                ]
            )
            await message.answer("Управление заказами:", reply_markup=keyboard)

        @self.dp.callback_query(F.data.startswith("admin_orders_"))
        async def admin_show_orders(callback: types.CallbackQuery):
            """Показать заказы для администратора"""
            is_admin = await self.is_manager(str(callback.from_user.id))
            if not is_admin:
                await callback.answer("❌ У вас нет прав")
                return

            status_map = {
                "admin_orders_all": None,
                "admin_orders_pending": "pending",
                "admin_orders_delivery": "delivery",
                "admin_orders_completed": "completed"
            }

            status = status_map.get(callback.data)
            if status:
                orders = await sync_to_async(list)(
                    Order.objects.filter(status=status).order_by('-order_date_time')[:10])
            else:
                orders = await sync_to_async(list)(Order.objects.all().order_by('-order_date_time')[:10])

            if not orders:
                await callback.message.answer("📭 Заказов нет")
                await callback.answer()
                return

            for order in orders:
                status_display = await sync_to_async(order.get_status_display)()
                delivery_display = await sync_to_async(order.get_delivery_method_display)()

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✏️ Статус", callback_data=f"admin_order_status_{order.id}"),
                            InlineKeyboardButton(text="📋 Детали", callback_data=f"admin_order_details_{order.id}")
                        ]
                    ]
                )

                order_info = f"""
📦 *Заказ №{order.order_number}*
👤 Клиент: {order.customer.first_name}
📞 Телефон: {order.customer.phone}
🏠 Адрес: {order.address}
🚚 Доставка: {delivery_display}
📊 Статус: {status_display}
💰 Сумма: {await sync_to_async(lambda: order.total_price)()} ₽
                """

                await callback.message.answer(order_info, parse_mode="Markdown", reply_markup=keyboard)

            await callback.answer()

        @self.dp.callback_query(F.data.startswith("admin_order_status_"))
        async def admin_change_order_status(callback: types.CallbackQuery):
            """Изменение статуса заказа администратором"""
            is_admin = await self.is_manager(str(callback.from_user.id))
            if not is_admin:
                await callback.answer("❌ У вас нет прав")
                return

            order_id = callback.data.replace("admin_order_status_", "")
            order = await sync_to_async(Order.objects.get)(id=order_id)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⏳ В обработке", callback_data=f"admin_set_status_{order.id}_pending")],
                    [InlineKeyboardButton(text="🚚 В доставке", callback_data=f"admin_set_status_{order.id}_delivery")],
                    [InlineKeyboardButton(text="✅ Завершен", callback_data=f"admin_set_status_{order.id}_completed")],
                    [InlineKeyboardButton(text="❌ Отменен", callback_data=f"admin_set_status_{order.id}_cancelled")]
                ]
            )

            await callback.message.edit_text(
                f"Выберите статус для заказа №{order.order_number}:",
                reply_markup=keyboard
            )
            await callback.answer()

        @self.dp.callback_query(F.data.startswith("admin_set_status_"))
        async def admin_set_order_status(callback: types.CallbackQuery):
            """Установка статуса заказа"""
            is_admin = await self.is_manager(str(callback.from_user.id))
            if not is_admin:
                await callback.answer("❌ У вас нет прав")
                return

            data = callback.data.split("_")
            order_id = data[3]
            new_status = data[4]

            order = await sync_to_async(Order.objects.get)(id=order_id)
            old_status = order.status
            order.status = new_status
            await sync_to_async(order.save)()

            status_display = dict(Order.STATUS_CHOICES).get(new_status, new_status)
            await callback.message.edit_text(
                f"✅ Статус заказа №{order.order_number} изменен на: {status_display}"
            )
            await callback.answer()

        @self.dp.message(F.text == "📊 Статистика")
        async def admin_statistics(message: types.Message):
            """Статистика магазина"""
            is_admin = await self.is_manager(str(message.from_user.id))
            if not is_admin:
                await message.answer("❌ У вас нет прав")
                return

            try:
                total_orders = await sync_to_async(Order.objects.count)()
                total_customers = await sync_to_async(Customer.objects.count)()
                total_products = await sync_to_async(Product.objects.count)()

                pending_orders = await sync_to_async(Order.objects.filter(status='pending').count)()
                delivery_orders = await sync_to_async(Order.objects.filter(status='delivery').count)()
                completed_orders = await sync_to_async(Order.objects.filter(status='completed').count)()

                total_revenue = await sync_to_async(
                    lambda: sum(order.total_price for order in Order.objects.filter(status='completed'))
                )()

                stats_text = f"""
📊 *Статистика магазина*

📦 Всего заказов: {total_orders}
👥 Клиентов: {total_customers}
🛍️ Товаров: {total_products}

📈 *Статусы заказов:*
⏳ В обработке: {pending_orders}
🚚 В доставке: {delivery_orders}
✅ Завершено: {completed_orders}

💰 Выручка: {total_revenue} ₽
                """

                await message.answer(stats_text, parse_mode="Markdown")

            except Exception as e:
                await message.answer("❌ Ошибка загрузки статистики")

        @self.dp.message(F.text == "🛍️ Управление товарами")
        async def admin_products_management(message: types.Message):
            """Управление товарами"""
            is_admin = await self.is_manager(str(message.from_user.id))
            if not is_admin:
                await message.answer("❌ У вас нет прав")
                return

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Список товаров", callback_data="admin_products_list")],
                    [InlineKeyboardButton(text="📊 Остатки", callback_data="admin_products_stock")]
                ]
            )
            await message.answer("Управление товарами:", reply_markup=keyboard)

        @self.dp.callback_query(F.data == "admin_products_list")
        async def admin_products_list(callback: types.CallbackQuery):
            """Список товаров для администратора"""
            is_admin = await self.is_manager(str(callback.from_user.id))
            if not is_admin:
                await callback.answer("❌ У вас нет прав")
                return

            products = await sync_to_async(list)(Product.objects.all()[:10])

            for product in products:
                product_info = f"""
🛍️ *{product.title}*
💰 Цена: {product.price} ₽
📦 Остаток: {product.remainder} шт.
📝 {product.description or 'Нет описания'}
                """

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ Редактировать",
                                              callback_data=f"admin_edit_product_{product.id}")]
                    ]
                )

                await callback.message.answer(product_info, parse_mode="Markdown", reply_markup=keyboard)

            await callback.answer()

    async def start_polling(self):
        """Запуск бота в режиме polling"""
        print("🤖 Telegram бот запущен")
        # Устанавливаем команды меню при запуске
        await self.set_bot_commands()
        await self.dp.start_polling(self.bot)

        self.dp.message.middleware(ManagerMiddleware())
        self.dp.callback_query.middleware(ManagerMiddleware())