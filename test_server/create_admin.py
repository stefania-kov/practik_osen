from test_site.models import CustomUser

user = CustomUser.objects.create(
    login='admin',
    email='admin@example.com',
    name='Admin',
    surname='User',
    patronymic='',
    rules_agreed=True,
    is_staff=True,
    is_superuser=True,
    is_active=True
)

user.set_password('admin123')
user.save()

print("✅ Админ создан!")
print("Логин: admin")
print("Пароль: admin123")