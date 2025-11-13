from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .forms import RegistrationForm, LoginForm
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem
import json

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаем корзину для нового пользователя
            Cart.objects.create(user=user)
            login(request, user)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect_url': '/'})
            return redirect('/')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = RegistrationForm()
    
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'redirect_url': '/'})
                return redirect('/')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

def index(request):
    return render(request, 'index.html')

def catalog(request):
    products = Product.objects.filter(in_stock=True)
    
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    sort = request.GET.get('sort', '-created_at')
    if sort in ['name', 'price', 'production_year', '-created_at']:
        products = products.order_by(sort)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'current_sort': sort,
        'current_category': category_slug,
    }
    return render(request, 'catalog.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, in_stock=True)
    
    context = {
        'product': product
    }
    return render(request, 'product_detail.html', context)

def contacts(request):
    return render(request, 'contacts.html')

@login_required
def cabinet(request):
    """Личный кабинет пользователя с заказами"""
    # Получаем заказы пользователя, отсортированные от новых к старым
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Статистика согласно новой модели Order (только 3 статуса)
    orders_count = orders.count()
    confirmed_orders = orders.filter(status='confirmed').count()
    cancelled_orders = orders.filter(status='cancelled').count()
    new_orders = orders.filter(status='new').count()
    
    context = {
        'orders': orders,
        'orders_count': orders_count,
        'confirmed_orders': confirmed_orders,
        'cancelled_orders': cancelled_orders,
        'new_orders': new_orders,
    }
    return render(request, 'cabinet.html', context)

@login_required
def delete_order(request, order_id):
    """Удаление заказа (только новые заказы)"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        if order.status != 'new':
            messages.error(request, 'Можно удалять только заказы со статусом "Новый"')
            return redirect('cabinet')
        
        if request.method == 'POST':
            order.delete()
            messages.success(request, f'Заказ #{order_id} успешно удален')
            return redirect('cabinet')
        else:
            messages.error(request, 'Неверный метод запроса')
            return redirect('cabinet')
            
    except Order.DoesNotExist:
        messages.error(request, 'Заказ не найден')
        return redirect('cabinet')


# ФУНКЦИИ КОРЗИНЫ
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    
    total_price = sum(item.get_total_price() for item in cart_items)
    total_quantity = sum(item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_quantity': total_quantity,
    }
    return render(request, 'cart.html', context)

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, in_stock=True)
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Получаем количество из запроса
        quantity = int(request.POST.get('quantity', 1))
        
        # Проверяем доступное количество
        if quantity > product.stock:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': f'Недостаточно товара в наличии. Доступно: {product.stock} шт.'
                })
            messages.error(request, f'Недостаточно товара в наличии. Доступно: {product.stock} шт.')
            return redirect('product_detail', slug=product.slug)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, 
            product=product
        )
        
        if not created:
            # Если товар уже в корзине, увеличиваем количество
            new_quantity = cart_item.quantity + quantity
            if new_quantity <= product.stock:
                cart_item.quantity = new_quantity
                cart_item.save()
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': f'Недостаточно товара в наличии. Всего можно добавить: {product.stock - cart_item.quantity} шт.'
                    })
                messages.error(request, f'Недостаточно товара в наличии. Всего можно добавить: {product.stock - cart_item.quantity} шт.')
                return redirect('product_detail', slug=product.slug)
        else:
            # Если товара нет в корзине, устанавливаем выбранное количество
            cart_item.quantity = quantity
            cart_item.save()
        
        # Получаем общее количество товаров в корзине
        total_quantity = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': f'Товар "{product.name}" добавлен в корзину ({quantity} шт.)',
                'cart_items_count': total_quantity
            })
        
        messages.success(request, f'Товар "{product.name}" добавлен в корзину ({quantity} шт.)')
        return redirect('cart_view')
    
    return redirect('catalog')

@login_required
def remove_from_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart = get_object_or_404(Cart, user=request.user)
        
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
        except CartItem.DoesNotExist:
            pass
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_items = CartItem.objects.filter(cart=cart)
            cart_items_count = cart_items.count()
            total_price = sum(item.get_total_price() for item in cart_items)
            
            return JsonResponse({
                'success': True,
                'cart_items_count': cart_items_count,
                'total_price': str(total_price)
            })
        
        return redirect('cart_view')
    
    return redirect('cart_view')

@login_required
def delete_from_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart = get_object_or_404(Cart, user=request.user)
        
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            cart_item.delete()
        except CartItem.DoesNotExist:
            pass
        
        return redirect('cart_view')
    
    return redirect('cart_view')

@login_required
def create_order(request):
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        
        if not cart_items:
            return JsonResponse({
                'success': False, 
                'error': 'Корзина пуста'
            })
        
        # Проверяем наличие товаров
        for item in cart_items:
            if item.quantity > item.product.stock:
                return JsonResponse({
                    'success': False, 
                    'error': f'Недостаточно товара: {item.product.name}'
                })
        
        # Проверяем пароль
        password = request.POST.get('password')
        user = authenticate(username=request.user.login, password=password)
        
        if user is not None:
            # Создаем заказ
            total_price = sum(item.get_total_price() for item in cart_items)
            order = Order.objects.create(user=request.user, total_price=total_price)
            
            # Создаем элементы заказа и обновляем остатки
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
                # Обновляем остатки
                item.product.stock -= item.quantity
                item.product.save()
            
            # Очищаем корзину
            cart_items.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Заказ #{order.id} успешно создан!',
                'order_id': order.id
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'Неверный пароль'
            })
    
    # GET запрос - показываем страницу оформления заказа
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.get_total_price() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'create_order.html', context)

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order
    }
    return render(request, 'order_success.html', context)