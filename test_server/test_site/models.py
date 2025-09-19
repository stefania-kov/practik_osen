from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
import re

class CustomUser(AbstractUser):
    patronymic = models.CharField(
        max_length=150, 
        blank=True, 
        verbose_name='Отчество'
    )
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='customuser_set', 
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set', 
        related_query_name='user',
    )
    
    def clean(self):
        super().clean()
        # Проверка имени, фамилии, отчества
        cyrillic_pattern = re.compile(r'^[А-Яа-яёЁ\s\-]+$')
        if self.first_name and not cyrillic_pattern.match(self.first_name):
            raise ValidationError({'first_name': 'Разрешены только кириллица, пробел и тире'})
        if self.last_name and not cyrillic_pattern.match(self.last_name):
            raise ValidationError({'last_name': 'Разрешены только кириллица, пробел и тире'})
        if self.patronymic and not cyrillic_pattern.match(self.patronymic):
            raise ValidationError({'patronymic': 'Разрешены только кириллица, пробел и тире'})
        
        # Проверка логина
        login_pattern = re.compile(r'^[a-zA-Z0-9\-]+$')
        if self.username and not login_pattern.match(self.username):
            raise ValidationError({'username': 'Разрешены только латиница, цифры и тире'})

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic or ''}".strip()