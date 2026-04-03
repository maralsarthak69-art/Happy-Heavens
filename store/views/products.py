from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from store.models import Product, Category


def product_list(request):
    """Home page — hero slider + paginated product grid (10 per page)."""
    qs = (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('images')
        .order_by('-created_at')
    )
    # New arrivals for hero slider — always top 5
    new_arrivals = list(qs[:5])

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'index.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'product_count': qs.count(),
        'new_arrivals': new_arrivals,
    })


def product_detail(request, slug):
    """Detail page for a single product."""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, 'product_detail.html', {
        'product': product,
        'out_of_stock': product.stock == 0,
    })


def product_detail_by_pk(request, pk):
    """Legacy PK-based URL — redirects to slug URL."""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return redirect('product_detail', slug=product.slug)


def category_detail(request, category_slug):
    """Category listing page, paginated at 12 per page."""
    category = get_object_or_404(Category, slug=category_slug)
    qs = (
        Product.objects.filter(category=category, is_active=True)
        .select_related('category')
        .prefetch_related('images')
    )
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'category_detail.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'category': category,
        'category_name': category.name,
    })
