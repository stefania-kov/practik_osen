from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import Category, Product, CustomUser, Cart, CartItem, Order, OrderItem
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.utils.html import format_html

# Кастомный фильтр для статусов заказов
class StatusFilter(admin.SimpleListFilter):
    title = 'Статус заказа'
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return [
            ('new', 'Новые'),
            ('confirmed', 'Подтвержденные'),
            ('cancelled', 'Отмененные'),
        ]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('login', 'email', 'surname', 'name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('login', 'email', 'surname', 'name')
    
    fieldsets = (
        (None, {'fields': ('login', 'password')}),
        (_('Personal info'), {'fields': ('surname', 'name', 'patronymic', 'email', 'rules_agreed')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('login', 'surname', 'name', 'patronymic', 'email', 'password1', 'password2', 'rules_agreed'),
        }),
    )
    
    ordering = ('login',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'in_stock', 'stock', 'created_at']
    list_filter = ['category', 'in_stock', 'created_at']
    search_fields = ['name', 'model', 'country']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'in_stock', 'stock']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at', 'get_total_price']
    list_filter = ['created_at']
    search_fields = ['user__login', 'user__email']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'added_at']
    list_filter = ['added_at']
    search_fields = ['product__name', 'cart__user__login']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'get_customer_name',  # ФИО вместо пользователя
        'created_at', 
        'total_price', 
        'status',
        'get_total_quantity', 
        'get_customer_contact'  # Контактная информация
    ]
    list_filter = [StatusFilter, 'created_at']
    list_editable = ['status']
    search_fields = ['user__login', 'user__email', 'user__surname', 'user__name']
    readonly_fields = [
        'created_at', 
        'total_price', 
        'get_customer_name', 
        'get_customer_contact',
        'get_order_items', 
        'get_total_quantity_display'
    ]
    actions = ['confirm_orders', 'cancel_orders_with_reason']
    list_per_page = 20
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'get_customer_name', 'get_customer_contact', 'created_at', 'total_price', 'get_total_quantity_display', 'status')
        }),
        ('Состав заказа', {
            'fields': ('get_order_items',),
            'classes': ('collapse',)
        }),
        ('Причина отказа', {
            'fields': ('cancellation_reason',),
            'description': 'Заполните это поле при отмене заказа. Пользователь увидит эту причину в своем кабинете.'
        }),
    )
    
    def get_customer_name(self, obj):
        return f"{obj.user.surname} {obj.user.name} {obj.user.patronymic or ''}".strip()
    get_customer_name.short_description = 'ФИО заказчика'
    
    def get_customer_contact(self, obj):
        contact_info = []
        if obj.user.email:
            contact_info.append(f"📧 {obj.user.email}")
        if obj.user.login:
            contact_info.append(f"👤 {obj.user.login}")
        return " | ".join(contact_info) if contact_info else "Контакт не указан"
    get_customer_contact.short_description = 'Контакты'
    
    def get_total_quantity(self, obj):
        return obj.get_total_quantity()
    get_total_quantity.short_description = 'Кол-во товаров'
    
    def get_total_quantity_display(self, obj):
        return f"{obj.get_total_quantity()} шт."
    get_total_quantity_display.short_description = 'Общее количество'
    
    def get_order_items(self, obj):
        items = []
        for item in obj.items.all():
            items.append(f"• {item.product.name} - {item.quantity} шт. × {item.price} ₽ = {item.get_total_price()} ₽")
        return "\n".join(items) if items else "Нет товаров"
    get_order_items.short_description = 'Товары в заказе'
    
    def confirm_orders(self, request, queryset):
        for order in queryset:
            if order.status != 'confirmed':
                order.status = 'confirmed'
                order.cancellation_reason = ''
                order.save()
        
        updated = queryset.count()
        self.message_user(request, f'{updated} заказов подтверждено')
    confirm_orders.short_description = "✅ Подтвердить выбранные заказы"
    
    def cancel_orders_with_reason(self, request, queryset):
        if 'apply' in request.POST:
            reason = request.POST.get('cancellation_reason', 'Причина не указана')
            for order in queryset:
                order.status = 'cancelled'
                order.cancellation_reason = reason
                order.save()
            
            updated = queryset.count()
            self.message_user(request, f'{updated} заказов отменено с причиной: {reason}')
            return None
        
        return render(request, 'admin/cancel_orders_with_reason.html', {
            'orders': queryset,
            'action': 'cancel_orders_with_reason',
        })
    cancel_orders_with_reason.short_description = "❌ Отменить заказы с указанием причины"
    
    def save_model(self, request, obj, form, change):
        if obj.status == 'cancelled' and not obj.cancellation_reason:
            obj.cancellation_reason = "Причина не указана администратором"
        elif obj.status != 'cancelled' and change:
            original = Order.objects.get(pk=obj.pk)
            if original.status == 'cancelled' and obj.status != 'cancelled':
                obj.cancellation_reason = ''
        
        super().save_model(request, obj, form, change)
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        cancellation_reason = cleaned_data.get('cancellation_reason')
        
        if status == 'cancelled' and not cancellation_reason:
            raise ValidationError({
                'cancellation_reason': 'При отмене заказа необходимо указать причину отказа.'
            })
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        
        if obj and obj.status != 'cancelled':
            fieldsets_list = list(fieldsets)
            for i, (title, data) in enumerate(fieldsets_list):
                if title == 'Причина отказа':
                    data['classes'] = ('collapse',)
                    break
            
            return fieldsets_list
        
        return fieldsets

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    list_filter = ['order__created_at']
    search_fields = ['product__name', 'order__user__login']