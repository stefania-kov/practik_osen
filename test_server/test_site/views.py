from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

def catalog(request):
    return render(request, 'catalog.html')

def contacts(request):
    return render(request, 'contacts.html')