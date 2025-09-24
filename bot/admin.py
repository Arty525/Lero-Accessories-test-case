from django.contrib import admin
from bot.models import Customer, Product, Category, Order, Cart, Manager


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    fields = ['first_name', 'last_name', 'phone', 'address', 'telegram_id']
    list_display = ('id', 'first_name', 'last_name', 'phone', 'address', 'telegram_id')
    search_fields = ('first_name', 'last_name', 'phone', 'address', 'telegram_id')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    fields = ['title', 'description', 'price', 'category', 'image']
    list_display = ('id', 'title', 'category', 'price')
    search_fields = ('title', 'description')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    fields = ['title', 'description']
    list_display = ('id', 'title', 'description')
    search_fields = ('title', 'description')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    fields = ['order_number', 'customer', 'is_confirmed', 'delivery_method', 'status']
    list_display = ('id', 'customer', 'order_date_time', 'is_confirmed', 'delivery_method', 'status')
    search_fields = ('customer', 'product')
    list_filter = ('is_confirmed', 'delivery_method', 'status')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    fields = ['customer', 'products']
    list_display = ('id', 'customer')
    search_fields = ('customer',)


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    fields = ['first_name', 'last_name', 'phone']
    list_display = ('id', 'first_name', 'last_name', 'phone')
    search_fields = ('first_name', 'last_name', 'phone')