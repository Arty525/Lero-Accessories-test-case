import asyncio
import types

from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from rest_framework.generics import RetrieveAPIView, DestroyAPIView, CreateAPIView, UpdateAPIView, ListAPIView
from rest_framework.renderers import JSONRenderer

from bot.models import Category, Product, Cart, Order, Customer
from bot.serializers import CategorySerializer, ProductSerializer, CartSerializer, OrderSerializer
from bot.services import order_number_generator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .bot import DjangoBot


bot = DjangoBot()

@csrf_exempt
@require_POST
def webhook(request):
    """Обработчик вебхуков от Telegram"""
    try:
        update = json.loads(request.body)
        asyncio.run(bot.dp.feed_update(bot.bot, types.Update(**update)))
        return HttpResponse("OK")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


class CategoriesAPIListView(ListAPIView):
    '''APIView для просмотра списка категорий'''

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    renderer_classes = [JSONRenderer]


class ProductsAPIListView(ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.filter(category=self.kwargs['category_id'])
        return queryset

class ProductsAPIRetrieveView(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductsAPICreateView(CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    model = Product


class ProductsAPIUpdateView(UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    model = Product


class ProductsAPIDestroyView(DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class CartAPICreateView(CreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer


class CartAPIRetrieveView(RetrieveAPIView):
    serializer_class = CartSerializer
    def get_queryset(self):
        cart = Cart.objects.get(customer = self.kwargs['customer_id'])
        return cart


class CartAPIUpdateView(UpdateAPIView):
    serializer_class = CartSerializer
    def get_queryset(self):
        cart = Cart.objects.get(customer = self.kwargs['customer_id'])
        return cart


class OrderAPIListView(ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class OrderAPIRetrieveView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class OrderAPICreateView(CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        customer = Customer.objects.create()
        order = serializer.save(customer=self.request.user)
        order_number = order_number_generator()


