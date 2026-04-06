from django.core.cache import cache
from django.db.models import Prefetch

from store.models import Category, Product
from .cart import Cart


def cart_count(request):
    return {'cart': Cart(request)}


def categories_processor(request):
    try:
        categories = cache.get('nav_categories')
        if categories is None:
            active_products = Prefetch(
                'products',
                queryset=Product.objects.filter(is_active=True),
            )
            categories = list(
                Category.objects.prefetch_related(active_products).all()
            )
            cache.set('nav_categories', categories, 60 * 15)
    except Exception:
        categories = []
    return {'categories': categories}
