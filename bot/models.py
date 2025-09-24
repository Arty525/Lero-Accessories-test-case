from django.db import models


class Category(models.Model):
    '''Модель категорий товаров'''
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.title


    class Meta:
        ordering = ['id', 'title']
        verbose_name_plural = 'Категории'
        verbose_name = 'Категория'


class Product(models.Model):
    '''Модель товара'''
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=500, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='media/products/')
    remainder = models.IntegerField(default=1)

    def __str__(self):
        return (f"{self.title} | {self.category} | {self.price}")

    class Meta:
        ordering = ['id', 'title']
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Customer(models.Model):
    '''Модель заказчика'''
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=100)
    telegram_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name} {self.phone}'

    class Meta:
        ordering = ['id', 'first_name', 'last_name']
        verbose_name = 'Заказчик'
        verbose_name_plural = 'Заказчики'


class Order(models.Model):
    '''Модель заказа'''
    DELIVERY_METHOD_CHOICES = (('self_pickup', 'Самовывоз'),
                               ('pick_up_point', 'В пункт выдачи'),
                               ('mail', 'Почтой'),
                               ('courier', 'Курьером'))

    STATUS_CHOICES = (('created', 'Создан'),
                      ('padding', 'Отправлен'),
                      ('delivered', 'Доставлен'),
                      ('cancelled', 'Отменен'))

    order_number = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    delivery_method = models.CharField(max_length=100, choices=DELIVERY_METHOD_CHOICES, default='self_pickup')
    is_confirmed = models.BooleanField(default=False)
    order_date_time = models.DateTimeField(auto_now=False, auto_now_add=True)
    address = models.CharField(max_length=200, default='Не указан')
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='created')

    @property
    def total_price(self):
        return sum(item.product.price * item.quantity for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def get_delivery_method_display(self):
        """Возвращает человеко-читаемое название способа доставки"""
        return dict(self.DELIVERY_METHOD_CHOICES).get(self.delivery_method, 'Не указан')

    def get_order_status(self):
        """Возвращает человеко-читаемое название статуса"""
        return dict(self.STATUS_CHOICES).get(self.status)

    def __str__(self):
        return (f'{self.order_number} | {self.customer.first_name} {self.customer.last_name} | {self.customer.phone}')

    class Meta:
        ordering = ['order_date_time', 'order_number']
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class Cart(models.Model):
    '''Модель корзины'''
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return f'Корзина {self.customer}'

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.product.price * item.quantity for item in self.items.all())

    class Meta:
        ordering = ['id']
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

class CartItem(models.Model):
    '''Модель элемента корзины'''
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.title} x{self.quantity}"

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ['cart', 'product']  # Уникальная пара корзина-товар


class OrderItem(models.Model):
    '''Модель элемента заказа'''
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.title} x{self.quantity}"

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'
        unique_together = ['order', 'product']  # Уникальная пара корзина-товар


class Manager(models.Model):
    '''Модель менеджера заказов'''
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=100, unique=True)
    is_staff = models.BooleanField(default=True)
    telegram_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name} {self.phone}'

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'