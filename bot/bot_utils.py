# bot_utils.py (обновленный)
import logging
from asgiref.sync import sync_to_async
from bot.models import Customer, Product, CartItem, Cart, OrderItem, Order
from bot.services import order_number_generator

# Настройка логирования
logger = logging.getLogger(__name__)

async def get_welcome_text(user) -> str:
    """Получение приветственного текста в зависимости от статуса пользователя"""
    try:
        logger.info(f"Получение приветственного текста для пользователя {user.id}")
        customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
        welcome_text = f"""С возвращением, {customer.first_name}!
✅ Вы уже зарегистрированы в системе как заказчик.
📞 Телефон: {customer.phone}
🏠 Адрес: {customer.address}
Выберите действие из меню ↓
"""
        logger.info(f"Пользователь {user.id} найден как заказчик")
        return welcome_text

    except Customer.DoesNotExist:
        logger.info(f"Пользователь {user.id} - новый, требуется регистрация")
        welcome_text = """
👋 Добро пожаловать! 
Я бот для управления заказами. Для завершения регистрации мне нужна дополнительная информация.
📝 Пожалуйста, введите ваш номер телефона в формате:
+79991234567
                    """
        return welcome_text

async def update_phone(user, phone) -> str:
    """Обновление номера телефона пользователя"""
    try:
        logger.info(f"Обновление телефона для пользователя {user.id}: {phone}")

        # Проверяем, не занят ли телефон другим пользователем
        phone_exists = await sync_to_async(
            lambda: Customer.objects.filter(phone=phone).exclude(telegram_id=str(user.id)).exists()
        )()

        if phone_exists:
            logger.warning(f"Телефон {phone} уже используется другим пользователем")
            return "❌ Этот номер телефона уже используется другим пользователем."

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

        if created:
            logger.info(f"Создан новый клиент: {customer.first_name} {customer.last_name}")
        else:
            logger.info(f"Обновлен телефон для существующего клиента: {customer.first_name}")

        return f"""
✅ Номер телефона сохранен: {phone}

Теперь введите ваш адрес:
(город, улица, дом, квартира)
        """

    except Exception as e:
        logger.error(f"Ошибка при обновлении телефона для пользователя {user.id}: {e}")
        return "❌ Ошибка при сохранении данных. Попробуйте еще раз."

async def update_address(user, address) -> str:
    """Обновление адреса пользователя"""
    try:
        logger.info(f"Обновление адреса для пользователя {user.id}: {address}")
        customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
        customer.address = address
        await sync_to_async(customer.save)()

        logger.info(f"Адрес успешно обновлен для пользователя {user.id}")
        success_text = f"""
Регистрация завершена!
📋 Ваши данные:
👤 Имя: {customer.first_name} {customer.last_name}
📞 Телефон: {customer.phone}
🏠 Адрес: {customer.address}
Теперь вы можете создавать заказы!
                    """
        return success_text
    except Customer.DoesNotExist:
        logger.warning(f"Попытка обновить адрес для незарегистрированного пользователя {user.id}")
        return "❌ Сначала введите номер телефона."
    except Exception as e:
        logger.error(f"Ошибка при обновлении адреса для пользователя {user.id}: {e}")
        return "❌ Ошибка при сохранении адреса."

async def get_profile(customer):
    """Получение информации о профиле"""
    logger.info(f"Запрос профиля для клиента {customer.id}")
    profile_info = f"""
📋 *Ваш профиль заказчика:*
👤 Имя: {customer.first_name} {customer.last_name}
📞 Телефон: `{customer.phone}`
🏠 Адрес: {customer.address}
🆔 Telegram ID: `{customer.telegram_id}`
"""
    return profile_info

async def add_item_in_cart(cart, product_id):
    """Добавление товара в корзину"""
    try:
        logger.info(f"Добавление товара {product_id} в корзину {cart.id}")
        product = await sync_to_async(Product.objects.get)(id=product_id)

        cart_item_exists = await sync_to_async(
            lambda: CartItem.objects.filter(cart=cart, product=product).exists()
        )()

        if cart_item_exists:
            cart_item = await sync_to_async(CartItem.objects.get)(cart=cart, product=product)
            cart_item.quantity += 1
            await sync_to_async(cart_item.save)()
            logger.info(f"Увеличено количество товара {product.title} в корзине")
            message = f"✅ Добавлена еще 1 шт. товара \"{product.title}\""
        else:
            await sync_to_async(CartItem.objects.create)(cart=cart, product=product, quantity=1)
            logger.info(f"Добавлен новый товар {product.title} в корзину")
            message = f"✅ Товар \"{product.title}\" добавлен в корзину"

        return message

    except Product.DoesNotExist:
        logger.error(f"Товар {product_id} не найден")
        return "❌ Товар не найден"
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара в корзину: {e}")
        return "❌ Ошибка при добавлении товара в корзину"

async def get_cart_data(customer):
    """Получение данных корзины"""
    try:
        logger.info(f"Получение данных корзины для клиента {customer.id}")
        cart = await sync_to_async(Cart.objects.get)(customer=customer)
        cart_data = await sync_to_async(
            lambda: list(cart.items.select_related('product').values(
                'product__id', 'product__title', 'product__price', 'quantity'
            ))
        )()
        total_items = await sync_to_async(lambda: cart.total_items)()
        total_price = await sync_to_async(lambda: cart.total_price)()

        logger.info(f"Корзина клиента {customer.id}: {total_items} товаров на сумму {total_price}")
        return cart_data, total_items, total_price

    except Cart.DoesNotExist:
        logger.warning(f"Корзина не найдена для клиента {customer.id}")
        return [], 0, 0
    except Exception as e:
        logger.error(f"Ошибка при получении данных корзины: {e}")
        return [], 0, 0

async def remove_item(customer, product_id):
    """Удаление товара из корзины"""
    error_message = '❌ Ошибка при удалении товара из корзины'
    try:
        logger.info(f"Удаление товара {product_id} из корзины клиента {customer.id}")
        cart = await sync_to_async(Cart.objects.get)(customer=customer)
        product = await sync_to_async(Product.objects.get)(id=product_id)
        cart_item = await sync_to_async(CartItem.objects.get)(cart=cart, product=product)
        await sync_to_async(cart_item.delete)()

        logger.info(f"Товар {product_id} успешно удален из корзины")
        return '✅ Товар удален из корзины'

    except Customer.DoesNotExist:
        logger.error(f"Клиент {customer.id} не найден при удалении товара")
        return error_message
    except Cart.DoesNotExist:
        logger.error(f"Корзина не найдена для клиента {customer.id}")
        return error_message
    except Product.DoesNotExist:
        logger.error(f"Товар {product_id} не найден при удалении")
        return error_message
    except CartItem.DoesNotExist:
        logger.error(f"Элемент корзины не найден для товара {product_id}")
        return error_message
    except Exception as e:
        logger.error(f'Ошибка при удалении товара: {e}')
        return error_message

async def change_cart_item_quantity(customer, product_id, quantity):
    """Изменение количества товара в корзине"""
    error_message = '❌ Ошибка при изменении количества товара в корзине'
    try:
        logger.info(f"Изменение количества товара {product_id} на {quantity} для клиента {customer.id}")
        cart = await sync_to_async(Cart.objects.get)(customer=customer)
        product = await sync_to_async(Product.objects.get)(id=product_id)
        cart_item = await sync_to_async(CartItem.objects.get)(cart=cart, product=product)
        cart_item.quantity = quantity
        await sync_to_async(cart_item.save)()

        logger.info(f"Количество товара {product_id} изменено на {quantity}")
        return '✅ Количество изменено'

    except Customer.DoesNotExist:
        logger.error(f"Клиент {customer.id} не найден при изменении количества")
        return error_message
    except Cart.DoesNotExist:
        logger.error(f"Корзина не найдена для клиента {customer.id}")
        return error_message
    except Product.DoesNotExist:
        logger.error(f"Товар {product_id} не найден при изменении количества")
        return error_message
    except CartItem.DoesNotExist:
        logger.error(f"Элемент корзины не найден для товара {product_id}")
        return error_message
    except Exception as e:
        logger.error(f'Ошибка при изменении количества товара: {e}')
        return error_message

async def new_order(customer, cart, delivery_method):
    """Создание нового заказа"""
    try:
        logger.info(f"Создание нового заказа для клиента {customer.id}, способ доставки: {delivery_method}")

        # Генерируем номер заказа
        order_number = await sync_to_async(order_number_generator)()
        logger.info(f"Сгенерирован номер заказа: {order_number}")

        # Создаем заказ
        order = await sync_to_async(Order.objects.create)(
            customer=customer,
            order_number=order_number,
            delivery_method=delivery_method,
            address=customer.address
        )

        # Получаем элементы корзины
        cart_items = await sync_to_async(list)(CartItem.objects.filter(cart=cart).select_related('product'))

        # Создаем элементы заказа
        for item in cart_items:
            await sync_to_async(OrderItem.objects.create)(
                order=order,
                product=item.product,
                quantity=item.quantity,
            )

        logger.info(f"Заказ {order_number} успешно создан, товаров: {len(cart_items)}")
        return (f'✅ Заказ успешно создан.\n'
                f'📦 Номер заказа: {order.order_number}\n'
                f'🏠 Адрес доставки: {customer.address}\n'
                f'🚚 Способ доставки: {order.get_delivery_method_display()}')

    except Exception as e:
        logger.error(f"Критическая ошибка при создании заказа: {e}")
        return '❌ Ошибка при создании заказа'
