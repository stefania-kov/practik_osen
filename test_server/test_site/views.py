from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, 
            product=product
        )
        
        if not created:
            if cart_item.quantity < product.stock:
                cart_item.quantity += 1
                cart_item.save()
        else:
            cart_item.quantity = 1
            cart_item.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_items_count = CartItem.objects.filter(cart=cart).count()
            return JsonResponse({
                'success': True, 
                'message': 'Товар добавлен в корзину',
                'cart_items_count': cart_items_count
            })
        
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