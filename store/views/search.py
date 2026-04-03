from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator

from store.models import Product, Category


def search(request):
    query = request.GET.get('q', '').strip()
    result_count = 0
    page_obj = None

    if query:
        qs = (
            Product.objects.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query),
                is_active=True,
            )
            .select_related('category')
            .prefetch_related('images')
        )
        result_count = qs.count()
        paginator = Paginator(qs, 12)
        page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'search_results.html', {
        'query': query,
        'results': page_obj,
        'result_count': result_count,
        'page_obj': page_obj,
        'categories': Category.objects.all(),
    })
