from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
import re
from django.urls import reverse

class CustomUser(AbstractUser):
    # Убираем стандартные поля first_name, last_name и username
    first_name = None
    last_name = None
    username = None  # Полностью убираем стандартное поле username
    
    # Добавляем поля точно по заданию
    name = models.CharField(
        max_length=150, 
        verbose_name='Имя'
    )
    surname = models.CharField(
        max_length=150, 
        verbose_name='Фамилия'
    )
    patronymic = models.CharField(
        max_length=150, 
        blank=True, 
        verbose_name='Отчество'
    )
    # Наше кастомное поле login вместо username
    login = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Логин'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )
    
    # Добавляем поле для хранения согласия с правилами в БД
    rules_agreed = models.BooleanField(
        default=False,
        verbose_name='Согласие с правилами'
    )
    
    # Убираем ненужные поля
    date_joined = None
    
    # Исправляем related_name чтобы избежать конфликтов
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_groups',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_permissions',
        related_query_name='custom_user',
    )
    
    # Указываем, что поле 'login' используется как username
    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['name', 'surname', 'email']
    
    def clean(self):
        super().clean()
        # Проверка имени, фамилии, отчества
        cyrillic_pattern = re.compile(r'^[А-Яа-яёЁ\s\-]+$')
        if self.name and not cyrillic_pattern.match(self.name):
            raise ValidationError({'name': 'Разрешены только кириллица, пробел и тире'})
        if self.surname and not cyrillic_pattern.match(self.surname):
            raise ValidationError({'surname': 'Разрешены только кириллица, пробел и тире'})
        if self.patronymic and not cyrillic_pattern.match(self.patronymic):
            raise ValidationError({'patronymic': 'Разрешены только кириллица, пробел и тире'})
        
        # Проверка логина
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']