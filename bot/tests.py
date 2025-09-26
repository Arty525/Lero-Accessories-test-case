# tests.py
import pytest
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from django.test import TestCase, RequestFactory
from asgiref.sync import sync_to_async

from bot.bot import DjangoBot
from bot.bot_utils import (
    get_welcome_text, update_phone, update_address, get_profile,
    add_item_in_cart, get_cart_data, remove_item, change_cart_item_quantity, new_order
)
from bot.models import Customer, Product, Cart, CartItem, Order
from bot.services import order_number_generator
from bot.views import webhook


class TestBotUtils(TestCase):
    """Тесты для утилит бота"""

    def setUp(self):
        # Настройка логирования для тестов
        logging.basicConfig(level=logging.CRITICAL)

        self.user = Mock()
        self.user.id = 123456
        self.user.first_name = "Test"
        self.user.last_name = "User"

    @pytest.mark.asyncio
    async def test_get_welcome_text_existing_customer(self):
        """Тест приветственного текста для существующего клиента"""
        # Создаем мок для Customer.objects.get
        mock_customer = Mock()
        mock_customer.first_name = "Test"
        mock_customer.phone = "+79991234567"
        mock_customer.address = "Test Address"

        with patch('bot.bot_utils.Customer.objects.get') as mock_get:
            # Настраиваем мок для синхронной функции
            mock_get.return_value = mock_customer

            # Используем sync_to_async для мока
            with patch('bot.bot_utils.sync_to_async') as mock_sync:
                mock_sync.return_value = AsyncMock(return_value=mock_customer)

                text = await get_welcome_text(self.user)
                self.assertIn("С возвращением", text)
                self.assertIn("Test", text)

    @pytest.mark.asyncio
    async def test_get_welcome_text_new_customer(self):
        """Тест приветственного текста для нового клиента"""
        # Мокаем sync_to_async чтобы вызывать исключение Customer.DoesNotExist
        with patch('bot.bot_utils.sync_to_async') as mock_sync:
            # Создаем асинхронную функцию-заглушку, которая вызывает исключение
            async def mock_async_func(*args, **kwargs):
                from bot.models import Customer
                raise Customer.DoesNotExist()

            mock_sync.return_value = mock_async_func

            text = await get_welcome_text(self.user)
            self.assertIn("Добро пожаловать", text)
            self.assertIn("номер телефона", text)

    @pytest.mark.asyncio
    async def test_update_phone_success(self):
        """Тест успешного обновления телефона"""
        # Мокаем проверку существования телефона
        with patch('bot.bot_utils.Customer.objects.filter') as mock_filter:
            mock_filter.return_value.exclude.return_value.exists.return_value = False

            # Мокаем get_or_create
            mock_customer = Mock()
            mock_customer.first_name = "Test"
            mock_customer.last_name = "User"
            mock_customer.phone = "+79991234567"
            mock_customer.address = "Не указан"

            with patch('bot.bot_utils.Customer.objects.get_or_create') as mock_get_or_create:
                mock_get_or_create.return_value = (mock_customer, True)  # created = True

                # Мокаем sync_to_async
                with patch('bot.bot_utils.sync_to_async') as mock_sync:
                    # Первый вызов - проверка exists
                    # Второй вызов - get_or_create
                    mock_sync.side_effect = [
                        AsyncMock(return_value=False),  # phone_exists = False
                        AsyncMock(return_value=(mock_customer, True))  # get_or_create
                    ]

                    result = await update_phone(self.user, "+79991234567")
                    self.assertIn("Номер телефона сохранен", result)

    @pytest.mark.asyncio
    async def test_update_phone_already_used(self):
        """Тест обновления телефона, который уже используется"""
        with patch('bot.bot_utils.sync_to_async') as mock_sync:
            mock_sync.return_value = AsyncMock(return_value=True)  # phone_exists = True

            result = await update_phone(self.user, "+79991234567")
            self.assertIn("уже используется", result)

    @pytest.mark.asyncio
    async def test_update_address_success(self):
        """Тест успешного обновления адреса"""
        mock_customer = Mock()
        mock_customer.first_name = "Test"
        mock_customer.last_name = "User"
        mock_customer.phone = "+79991234567"
        mock_customer.address = "Old Address"

        with patch('bot.bot_utils.Customer.objects.get') as mock_get:
            mock_get.return_value = mock_customer

            with patch('bot.bot_utils.sync_to_async') as mock_sync:
                # Первый вызов - get
                # Второй вызов - save
                mock_sync.side_effect = [
                    AsyncMock(return_value=mock_customer),
                    AsyncMock(return_value=None)  # save
                ]

                result = await update_address(self.user, "New Address")
                self.assertIn("Регистрация завершена", result)

    @pytest.mark.asyncio
    async def test_update_address_customer_not_found(self):
        """Тест обновления адреса для несуществующего клиента"""
        with patch('bot.bot_utils.Customer.objects.get') as mock_get:
            mock_get.side_effect = Customer.DoesNotExist()

            with patch('bot.bot_utils.sync_to_async') as mock_sync:
                mock_sync.return_value = AsyncMock(side_effect=Customer.DoesNotExist())

                result = await update_address(self.user, "New Address")
                self.assertIn("Сначала введите номер телефона", result)


class TestCartFunctions(TestCase):
    """Тесты функций корзины"""

    def setUp(self):
        self.customer = Mock()
        self.cart = Mock()
        self.product = Mock()
        self.product.id = 1
        self.product.title = "Test Product"
        self.product.price = 100

    @pytest.mark.asyncio
    async def test_add_item_to_cart_new(self):
        """Тест добавления нового товара в корзину"""
        with patch('bot.bot_utils.Product.objects.get') as mock_product_get:
            mock_product_get.return_value = self.product

            with patch('bot.bot_utils.CartItem.objects.filter') as mock_filter:
                mock_filter.return_value.exists.return_value = False  # Товара нет в корзине

                with patch('bot.bot_utils.CartItem.objects.create') as mock_create:
                    with patch('bot.bot_utils.sync_to_async') as mock_sync:
                        mock_sync.side_effect = [
                            AsyncMock(return_value=self.product),  # Product.objects.get
                            AsyncMock(return_value=False),  # exists
                            AsyncMock(return_value=None)  # create
                        ]

                        result = await add_item_in_cart(self.cart, "1")
                        self.assertIn("добавлен в корзину", result)

    @pytest.mark.asyncio
    async def test_add_item_to_cart_existing(self):
        """Тест добавления существующего товара в корзину"""
        mock_cart_item = Mock()
        mock_cart_item.quantity = 1

        with patch('bot.bot_utils.Product.objects.get') as mock_product_get:
            mock_product_get.return_value = self.product

            with patch('bot.bot_utils.CartItem.objects.filter') as mock_filter:
                mock_filter.return_value.exists.return_value = True  # Товар уже в корзине

                with patch('bot.bot_utils.CartItem.objects.get') as mock_get:
                    mock_get.return_value = mock_cart_item

                    with patch('bot.bot_utils.sync_to_async') as mock_sync:
                        mock_sync.side_effect = [
                            AsyncMock(return_value=self.product),  # Product.objects.get
                            AsyncMock(return_value=True),  # exists
                            AsyncMock(return_value=mock_cart_item),  # get
                            AsyncMock(return_value=None)  # save
                        ]

                        result = await add_item_in_cart(self.cart, "1")
                        self.assertIn("Добавлена еще 1 шт.", result)

    @pytest.mark.asyncio
    async def test_remove_item_success(self):
        """Тест успешного удаления товара из корзины"""
        mock_cart_item = Mock()

        with patch('bot.bot_utils.Cart.objects.get') as mock_cart_get:
            mock_cart_get.return_value = self.cart

            with patch('bot.bot_utils.Product.objects.get') as mock_product_get:
                mock_product_get.return_value = self.product

                with patch('bot.bot_utils.CartItem.objects.get') as mock_cart_item_get:
                    mock_cart_item_get.return_value = mock_cart_item

                    with patch('bot.bot_utils.sync_to_async') as mock_sync:
                        mock_sync.side_effect = [
                            AsyncMock(return_value=self.cart),  # Cart.objects.get
                            AsyncMock(return_value=self.product),  # Product.objects.get
                            AsyncMock(return_value=mock_cart_item),  # CartItem.objects.get
                            AsyncMock(return_value=None)  # delete
                        ]

                        result = await remove_item(self.customer, "1")
                        self.assertIn("Товар удален из корзины", result)

    @pytest.mark.asyncio
    async def test_remove_item_not_found(self):
        """Тест удаления несуществующего товара"""
        with patch('bot.bot_utils.sync_to_async') as mock_sync:
            mock_sync.side_effect = Exception("Not found")

            result = await remove_item(self.customer, "999")
            self.assertIn("Ошибка при удалении", result)


class TestOrderFunctions(TestCase):
    """Тесты функций заказов"""

    def setUp(self):
        self.customer = Mock()
        self.customer.address = "Test Address"
        self.cart = Mock()

    @pytest.mark.asyncio
    async def test_new_order_success(self):
        """Тест успешного создания заказа"""
        mock_order = Mock()
        mock_order.order_number = "AB1234010125"
        mock_order.get_delivery_method_display.return_value = "Самовывоз"

        mock_cart_items = [Mock(), Mock()]

        with patch('bot.bot_utils.order_number_generator') as mock_generator:
            mock_generator.return_value = "AB1234010125"

            with patch('bot.bot_utils.Order.objects.create') as mock_order_create:
                mock_order_create.return_value = mock_order

                with patch('bot.bot_utils.CartItem.objects.filter') as mock_filter:
                    mock_filter.return_value.select_related.return_value = mock_cart_items

                    with patch('bot.bot_utils.OrderItem.objects.create') as mock_order_item_create:
                        with patch('bot.bot_utils.sync_to_async') as mock_sync:
                            mock_sync.side_effect = [
                                AsyncMock(return_value="AB1234010125"),  # order_number_generator
                                AsyncMock(return_value=mock_order),  # Order.objects.create
                                AsyncMock(return_value=mock_cart_items),  # CartItem.objects.filter
                                AsyncMock(return_value=None),  # OrderItem.objects.create
                                AsyncMock(return_value=None)  # OrderItem.objects.create (второй раз)
                            ]

                            result = await new_order(self.customer, self.cart, "self_pickup")
                            self.assertIn("Заказ успешно создан", result)
                            self.assertIn("AB1234010125", result)

    @pytest.mark.asyncio
    async def test_new_order_error(self):
        """Тест ошибки при создании заказа"""
        with patch('bot.bot_utils.sync_to_async') as mock_sync:
            mock_sync.side_effect = Exception("Database error")

            result = await new_order(self.customer, self.cart, "self_pickup")
            self.assertIn("Ошибка при создании заказа", result)


class TestServices(TestCase):
    """Тесты сервисных функций"""

    def test_order_number_generator_success(self):
        """Тест успешной генерации номера заказа"""
        with patch('bot.services.random.randint') as mock_randint, \
                patch('bot.services.random.choices') as mock_choices, \
                patch('bot.services.datetime') as mock_datetime:
            mock_choices.return_value = ['A', 'B']
            mock_randint.return_value = 1234

            mock_now = Mock()
            mock_now.day = 1
            mock_now.month = 1
            mock_now.year = 2024
            mock_datetime.now.return_value = mock_now

            result = order_number_generator()
            self.assertTrue(result.startswith("AB"))
            self.assertIn("1234", result)

    def test_order_number_generator_fallback(self):
        """Тест резервной генерации номера заказа при ошибке"""
        with patch('bot.services.random.randint') as mock_randint, \
                patch('bot.services.random.choices') as mock_choices:
            mock_choices.side_effect = Exception("Random error")
            mock_randint.return_value = 9999

            result = order_number_generator()
            self.assertTrue(result.startswith("EM"))


class TestErrorHandling(TestCase):
    """Тесты обработки ошибок"""

    @pytest.mark.asyncio
    async def test_network_errors(self):
        """Тест обработки сетевых ошибок"""
        with patch('bot.bot_utils.sync_to_async') as mock_sync:
            mock_sync.side_effect = TimeoutError("Network timeout")

            result = await update_phone(Mock(), "+79991234567")
            self.assertIn("Ошибка при сохранении", result)


# Дополнительные тесты для полного покрытия
class TestAdditionalCases(TestCase):
    """Дополнительные тестовые случаи"""

    @pytest.mark.asyncio
    async def test_get_profile(self):
        """Тест получения профиля"""
        mock_customer = Mock()
        mock_customer.first_name = "Test"
        mock_customer.last_name = "User"
        mock_customer.phone = "+79991234567"
        mock_customer.address = "Test Address"
        mock_customer.telegram_id = "123456"

        result = await get_profile(mock_customer)
        self.assertIn("Test User", result)
        self.assertIn("+79991234567", result)

    @pytest.mark.asyncio
    async def test_get_cart_data_empty(self):
        """Тест получения данных пустой корзины"""
        mock_customer = Mock()
        mock_cart = Mock()
        mock_cart.total_items = 0
        mock_cart.total_price = 0

        with patch('bot.bot_utils.Cart.objects.get') as mock_cart_get:
            mock_cart_get.return_value = mock_cart

            with patch('bot.bot_utils.sync_to_async') as mock_sync:
                mock_sync.side_effect = [
                    AsyncMock(return_value=mock_cart),
                    AsyncMock(return_value=[]),  # cart_data
                    AsyncMock(return_value=0),  # total_items
                    AsyncMock(return_value=0)  # total_price
                ]

                cart_data, total_items, total_price = await get_cart_data(mock_customer)
                self.assertEqual(cart_data, [])
                self.assertEqual(total_items, 0)
                self.assertEqual(total_price, 0)

    @pytest.mark.asyncio
    async def test_change_cart_item_quantity_success(self):
        """Тест успешного изменения количества товара"""
        mock_customer = Mock()
        mock_cart = Mock()
        mock_product = Mock()
        mock_cart_item = Mock()

        with patch('bot.bot_utils.Cart.objects.get') as mock_cart_get:
            mock_cart_get.return_value = mock_cart

            with patch('bot.bot_utils.Product.objects.get') as mock_product_get:
                mock_product_get.return_value = mock_product

                with patch('bot.bot_utils.CartItem.objects.get') as mock_cart_item_get:
                    mock_cart_item_get.return_value = mock_cart_item

                    with patch('bot.bot_utils.sync_to_async') as mock_sync:
                        mock_sync.side_effect = [
                            AsyncMock(return_value=mock_cart),
                            AsyncMock(return_value=mock_product),
                            AsyncMock(return_value=mock_cart_item),
                            AsyncMock(return_value=None)  # save
                        ]

                        result = await change_cart_item_quantity(mock_customer, "1", 5)
                        self.assertIn("Количество изменено", result)


# Запуск тестов
if __name__ == '__main__':
    pytest.main()