from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from store.models import Order


@login_required
def my_orders(request):
    """Paginated order history for the logged-in user (10 per page)."""
    qs = (
        Order.objects.filter(user=request.user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'my_orders.html', {'orders': page_obj, 'page_obj': page_obj})


@login_required
def order_detail(request, pk):
    """Single order detail — returns 403 if the order belongs to another user."""
    order = get_object_or_404(Order, pk=pk)
    if order.user != request.user:
        return HttpResponseForbidden("You do not have permission to view this order.")
    items = order.items.select_related('product').all()
    return render(request, 'order_detail.html', {'order': order, 'items': items})
