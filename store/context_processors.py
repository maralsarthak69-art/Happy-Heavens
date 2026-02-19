from store.models import Category
from .cart import Cart

def cart_count(request):
    return {'cart': Cart(request)}

def categories_processor(request):
    return {'categories': Category.objects.all()}