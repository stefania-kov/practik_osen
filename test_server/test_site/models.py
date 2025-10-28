from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
import re
from django.urls import reverse
from django.utils import timezone

class CustomUser(AbstractUser):
    # Убираем стандартные поля first_name, last_name и username
    first_name = None
    last_name = None
    username = None
    
    # Добавляем поля точно по заданию
    name = models.CharField(max_length=150, verbose_name='Имя')
    surname = models.CharField(max_length=150, verbose_name='Фамилия')
    patronymic = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    login = models.CharField(max_length=150, unique=True, verbose_name='Логин')
    email = models.EmailField(unique=True, verbose_name='Email')
    rules_agreed = models.BooleanField(default=False, verbose_name='Согласие с правилами')
    
    # Восстанавливаем необходимые поля
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Дата регистрации')
    is_active = models.BooleanField(default=True, verbose_name='Активный')
    is_staff = models.BooleanField(default=False, verbose_name='Персонал')
    is_superuser = models.BooleanField(default=False, verbose_name='Суперпользователь')
    
    # Исправляем related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='custom_user_groups',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='custom_user_permissions',
        related_query_name='custom_user',
    )
    
    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['name', 'surname', 'email']
    
    def clean(self):
        super().clean()
        cyrillic_pattern = re.compile(r'^[А-Яа-яёЁ\s\-]+$')
        if self.name and not cyrillic_pattern.match(self.name):
            raise ValidationError({'name': 'Разрешены только кириллица, пробел и тире'})
        if self.surname and not cyrillic_pattern.match(self.surname):
            raise ValidationError({'surname': 'Разрешены только кириллица, пробел и тире'})
        if self.patronymic and not cyrillic_pattern.match(self.patronymic):
            raise ValidationError({'patronymic': 'Разрешены только кириллица, пробел и тире'})
        
        login_pattern = re.compile(r'^[a-zA-Z0-9\-]+$')
        if self.login and not login_pattern.match(self.login):
            raise ValidationError({'login': 'Разрешены только латиница, цифры и тире'})

    def __str__(self):
        return f"{self.surname} {self.name} {self.patronymic or ''}".strip()

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='Наименование')
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    image = models.ImageField(upload_to='products/', verbose_name='Изображение')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория')
    country = models.CharField(max_length=100, verbose_name='Страна-производитель')
    production_year = models.IntegerField(verbose_name='Год выпуска')
    model = models.CharField(max_length=100, verbose_name='Модель')
    in_stock = models.BooleanField(default=True, verbose_name='В наличии')
    stock = models.IntegerField(default=0, verbose_name='Количество на складе')  # Добавили поле stock
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

# МОДЕЛИ ДЛЯ КОРЗИНЫ И ЗАКАЗОВ
class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    def __str__(self):
        return f"Корзина пользователя {self.user.login}"
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    def get_total_quantity(self):
        return sum(item.quantity for item in self.items.all())
    
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='Корзина')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def get_total_price(self):
        return self.product.price * self.quantity
    
    def clean(self):
        if self.quantity > self.product.stock:
            raise ValidationError(f'Недостаточно товара на складе. Доступно: {self.product.stock}')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ['cart', 'product']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Общая стоимость')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус заказа')
    
    def __str__(self):
        return f"Заказ #{self.id} от {self.user.login}"
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Товар')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент заказа')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def get_total_price(self):
        return self.price * self.quantity
    
    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'