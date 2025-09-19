from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser
import re

class RegistrationForm(UserCreationForm):
    name = forms.CharField(
        max_length=150, 
        label='Имя*',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    surname = forms.CharField(
        max_length=150, 
        label='Фамилия*',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    patronymic = forms.CharField(
        max_length=150, 
        required=False,
        label='Отчество',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    login = forms.CharField(
        max_length=150, 
        label='Логин*',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label='Email*',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Пароль*',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=6
    )
    password2 = forms.CharField(
        label='Повторите пароль*',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    rules = forms.BooleanField(
        label='Я согласен с правилами регистрации',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = CustomUser
        fields = ['name', 'surname', 'patronymic', 'login', 'email', 'password1', 'password2', 'rules']

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[А-Яа-яёЁ\s\-]+$', name):
            raise ValidationError('Разрешены только кириллица, пробел и тире')
        return name

    def clean_surname(self):
        surname = self.cleaned_data['surname']
        if not re.match(r'^[А-Яа-яёЁ\s\-]+$', surname):
            raise ValidationError('Разрешены только кириллица, пробел и тире')
        return surname

    def clean_patronymic(self):
        patronymic = self.cleaned_data['patronymic']
        if patronymic and not re.match(r'^[А-Яа-яёЁ\s\-]+$', patronymic):
            raise ValidationError('Разрешены только кириллица, пробел и тире')
        return patronymic

    def clean_login(self):
        login = self.cleaned_data['login']
        if not re.match(r'^[a-zA-Z0-9\-]+$', login):
            raise ValidationError('Разрешены только латиница, цифры и тире')
        if CustomUser.objects.filter(username=login).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return login

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError({'password2': 'Пароли не совпадают'})
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['name']
        user.last_name = self.cleaned_data['surname']
        user.patronymic = self.cleaned_data['patronymic']
        user.username = self.cleaned_data['login']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин или Email',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )