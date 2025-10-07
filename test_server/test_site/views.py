from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from .forms import RegistrationForm, LoginForm
from django.db.models import Q
from .models import Product, Category

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
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
    
    # Фильтрация по категориям
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Сортировка
    sort = request.GET.get('sort', '-created_at')
    if sort in ['name', 'price', 'production_year', '-created_at']:
        products = products.order_by(sort)
    
    # Получаем все категории для фильтра
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