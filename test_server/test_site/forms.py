from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser
import re

class RegistrationForm(UserCreationForm):
    # Поле для согласия с правилами (сохраняется в модель как rules_agreed)
    rules = forms.BooleanField(
        required=True,
        label='Я согласен с правилами регистрации',
        error_messages={'required': 'Вы должны согласиться с правилами регистрации'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = CustomUser
        fields = ['name', 'surname', 'patronymic', 'login', 'email', 'password1', 'password2', 'rules']
        labels = {
            'name': 'Имя*',
            'surname': 'Фамилия*', 
            'patronymic': 'Отчество',
            'login': 'Логин*',
            'email': 'Email*',
            'password1': 'Пароль*',
            'password2': 'Повторите пароль*',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'login': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Минимум 6 символов'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Отключаем стандартную валидацию паролей Django
        self.fields['password1'].validators = []
        self.fields['password2'].validators = []

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
        if CustomUser.objects.filter(login=login).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return login

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 6:
            raise ValidationError('Пароль должен содержать не менее 6 символов')
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают')
        
        return password2

    def _post_clean(self):
        # Переопределяем метод, чтобы пропустить стандартную валидацию паролей
        super(forms.ModelForm, self)._post_clean()

    def save(self, commit=True):
        # Сохраняем согласие с правилами в поле rules_agreed
        user = super().save(commit=False)
        user.rules_agreed = self.cleaned_data['rules']
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Латиница, цифры и тире'
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Минимум 6 символов'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Проверка на разрешенные символы (латиница, цифры, тире)
            if not re.match(r'^[a-zA-Z0-9\-]+$', username):
                raise ValidationError('Логин может содержать только латинские буквы, цифры и тире')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 6:
            raise ValidationError('Пароль должен содержать не менее 6 символов')
        return password