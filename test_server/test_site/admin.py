from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'in_stock', 'created_at']
    list_filter = ['category', 'in_stock', 'created_at']
    search_fields = ['name', 'model', 'country']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'in_stock']  # Можно редактировать прямо в списке
    
    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'category', 'price', 'image')
        }),
        ('Характеристики', {
            'fields': ('country', 'production_year', 'model')
        }),
        ('Наличие', {
            'fields': ('in_stock',)
        }),
    )