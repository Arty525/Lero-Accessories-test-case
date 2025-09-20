from asgiref.sync import sync_to_async

from bot.models import Customer, Product, CartItem, Cart


async def get_welcome_text(user) -> str:
    try:
        customer = await sync_to_async(Customer.objects.get)(telegram_id=str(user.id))
        welcome_text = f"""
С возвращением, {customer.first_name}!
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
    products_text = 'Список товаров в корзине:\n\n'
    cart_data = await sync_to_async(
        lambda: list(cart.items.select_related('product').values(
            'product__title', 'product__price', 'quantity'
        ))
    )()
    for item in cart_data:
        products_text += f"{item['product__title']} - {item['product__price']} ₽ | {item['quantity']} шт.\n"
    # Асинхронно получаем общие данные
    total_items = await sync_to_async(lambda: cart.total_items)()
    total_price = await sync_to_async(lambda: cart.total_price)()

    products_text += f'Всего товаров: {total_items}\nИтого: {total_price} ₽'

    return products_text