from asgiref.sync import sync_to_async
from bot.models import Customer, Product, CartItem, Cart, OrderItem, Order, Manager
from bot.services import order_number_generator


async def get_welcome_text(user) -> str:
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
        welcome_text = f"""С возвращением, {customer.first_name}!
✅ Вы уже зарегистрированы в системе как заказчик.
📞 Телефон: {customer.phone}
🏠 Адрес: {customer.address}
Выберите действие из меню ↓
"""

    except Customer.DoesNotExist:
        try:
            manager = await sync_to_async(Manager.objects.get)(telegram_id=str(user.id))
            welcome_text = 'Для входа в панель администратора введите команду /admin'
        except Manager.DoesNotExist:
            welcome_text = """
    👋 Добро пожаловать! 
    Я бот для управления заказами. Для завершения регистрации мне нужна дополнительная информация.
    📝 Пожалуйста, введите ваш номер телефона в формате:
    +79991234567
                        """
    return welcome_text

async def update_phone(user, phone) -> str:
    try:
        # Проверяем, не занят ли телефон другим пользователем
        phone_exists = await sync_to_async(
            lambda: Customer.objects.filter(phone=phone).exclude(telegram_id=str(user.id)).exists()
        )()

        if phone_exists:
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

        if not created:
            # Обновляем телефон если пользователь уже существует
            customer.phone = phone
            await sync_to_async(customer.save)()

        return f"""
✅ Номер телефона сохранен: {phone}

Теперь введите ваш адрес:
(город, улица, дом, квартира)
        """

    except Exception as e:
        print('Ошибка:', e)
        return "❌ Ошибка при сохранении данных. Попробуйте еще раз."


async def update_address(user, address) -> str:
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
        customer.address = address
        await sync_to_async(customer.save)()
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
        return ("❌ Сначала введите номер телефона.")
    except Exception as e:
        return ("❌ Ошибка при сохранении адреса.")

async def get_profile(customer):
    profile_info = f"""
📋 *Ваш профиль заказчика:*
👤 Имя: {customer.first_name} {customer.last_name}
📞 Телефон: `{customer.phone}`
🏠 Адрес: {customer.address}
🆔 Telegram ID: `{customer.telegram_id}`
"""
    return profile_info

async def add_item_in_cart(cart, product_id):
    product = await sync_to_async(Product.objects.get)(id=product_id)

    cart_item_exists = await sync_to_async(
        lambda: CartItem.objects.filter(cart=cart, product=product).exists()
    )()

    if cart_item_exists:
        cart_item = await sync_to_async(
            CartItem.objects.get
        )(cart=cart, product=product)
        cart_item.quantity += 1
        await sync_to_async(cart_item.save)()
        message = f"✅ Добавлена еще 1 шт. товара \"{product.title}\""
    else:
        await sync_to_async(
            CartItem.objects.create
        )(cart=cart, product=product, quantity=1)
        message = f"✅ Товар \"{product.title}\" добавлен в корзину"

    return message

async def get_cart_data(customer) -> str:
    cart = await sync_to_async(Cart.objects.get)(customer=customer)
    cart_data = await sync_to_async(
        lambda: list(cart.items.select_related('product').values(
            'product__id', 'product__title', 'product__price', 'quantity'
        ))
    )()
    total_items = await sync_to_async(lambda: cart.total_items)()
    total_price = await sync_to_async(lambda: cart.total_price)()

    return cart_data, total_items, total_price


async def remove_item(customer, product_id):
    error_message = '❌ Ошибка при удалении товара из корзины'
    try:
        cart = await sync_to_async(Cart.objects.get)(customer=customer)
        product = await sync_to_async(Product.objects.get)(id=product_id)
        cart_item = await sync_to_async(CartItem.objects.get)(cart=cart, product=product)
        await sync_to_async(cart_item.delete)()
        return '✅ Товар удален из корзины'

    except Customer.DoesNotExist:
        return error_message
    except Cart.DoesNotExist:
        return error_message
    except Product.DoesNotExist:
        return error_message
    except CartItem.DoesNotExist:
        return error_message
    except Exception as e:
        print(f'Ошибка: {e}')
        return error_message

async def change_cart_item_quantity(customer, product_id, quantity):
    error_message = '❌ Ошибка при изменении количества товара в корзине'
    try:
        cart = await sync_to_async(Cart.objects.get)(customer=customer)
        product = await sync_to_async(Product.objects.get)(id=product_id)
        cart_item = await sync_to_async(CartItem.objects.get)(cart=cart, product=product)
        cart_item.quantity = quantity
        await sync_to_async(cart_item.save)()
        return '✅ Количество изменено'

    except Customer.DoesNotExist:
        return error_message
    except Cart.DoesNotExist:
        return error_message
    except Product.DoesNotExist:
        return error_message
    except CartItem.DoesNotExist:
        return error_message
    except Exception as e:
        print(f'Ошибка: {e}')
        return error_message


async def new_order(customer, cart, delivery_method):
    try:
        # Генерируем номер заказа
        order_number = await sync_to_async(order_number_generator)()

        # Создаем заказ
        order = await sync_to_async(Order.objects.create)(
            customer=customer,
            order_number=order_number,
            delivery_method=delivery_method
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


        return (f'✅ Заказ успешно создан.\n'
                f'📦 Номер заказа: {order.order_number}\n'
                f'🏠 Адрес доставки: {customer.address}\n'
                f'🚚 Способ доставки: {order.get_delivery_method_display()}')

    except Exception as e:
        print(f"Ошибка при создании заказа: {e}")
        return '❌ Ошибка при создании заказа'


@sync_to_async
def is_manager(user_id):
    """Проверяет, является ли пользователь менеджером"""
    try:
        manager = Manager.objects.get(phone=user_id)  # или telegram_id, если добавите поле
        return manager.is_staff
    except Manager.DoesNotExist:
        return False

@sync_to_async
def get_manager(user_id):
    """Получает объект менеджера"""
    try:
        return Manager.objects.get(phone=user_id)
    except Manager.DoesNotExist:
        return None