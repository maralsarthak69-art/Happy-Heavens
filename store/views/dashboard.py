"""
Owner Dashboard — /dashboard/
Staff-only page giving a full at-a-glance view of the store.
Handles:
  • Summary stats (today's orders, pending, revenue, low stock, new custom requests)
  • Recent orders list with inline status update
  • New custom requests list
  • Low-stock product list
"""
from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.timezone import now

from store.models import Order, CustomRequest, Product


# ─────────────────────────────────────────────────────────────────────────────
# Status display helpers (same palette as admin.py)
# ─────────────────────────────────────────────────────────────────────────────
STATUS_META = {
    'PENDING':   {'label': '⏳ Pending',          'bg': 'bg-amber-100',  'text': 'text-amber-800'},
    'CONFIRMED': {'label': '✅ Confirmed',         'bg': 'bg-blue-100',   'text': 'text-blue-800'},
    'SHIPPED':   {'label': '🚚 Out for Delivery',  'bg': 'bg-purple-100', 'text': 'text-purple-800'},
    'DELIVERED': {'label': '🎉 Delivered',         'bg': 'bg-green-100',  'text': 'text-green-800'},
    'REJECTED':  {'label': '❌ Rejected',          'bg': 'bg-red-100',    'text': 'text-red-800'},
}

# All statuses available in the dropdown on the dashboard
STATUS_CHOICES = [
    ('PENDING',   '⏳ Pending'),
    ('CONFIRMED', '✅ Confirmed'),
    ('SHIPPED',   '🚚 Out for Delivery'),
    ('DELIVERED', '🎉 Delivered'),
    ('REJECTED',  '❌ Rejected'),
]


@staff_member_required(login_url='/login/')
def dashboard(request):
    """Main dashboard view — read-only summary + recent data."""
    today = now().date()

    # ── Stats ────────────────────────────────────────────────────────────────
    orders_today   = Order.objects.filter(created_at__date=today).count()
    pending_orders = Order.objects.filter(status='PENDING').count()
    confirmed_orders = Order.objects.filter(status='CONFIRMED').count()
    total_revenue  = sum(
        o.total_amount
        for o in Order.objects.filter(status='DELIVERED')
    )
    new_requests   = CustomRequest.objects.filter(submitted_at__date=today).count()
    low_stock      = Product.objects.filter(is_active=True, stock__lte=3).order_by('stock')

    # ── Recent orders (last 20) ───────────────────────────────────────────────
    recent_orders = (
        Order.objects
        .select_related('user')
        .prefetch_related('items__product')
        .order_by('-created_at')[:20]
    )
    # Attach status meta to each order for template rendering
    orders_with_meta = [
        {
            'order': o,
            'meta':  STATUS_META.get(o.status, STATUS_META['PENDING']),
            'items_summary': ', '.join(
                f"{i.quantity}× {i.product.name if i.product else 'Deleted product'}"
                for i in o.items.all()
            ),
        }
        for o in recent_orders
    ]

    # ── New custom requests (last 10) ─────────────────────────────────────────
    custom_requests = CustomRequest.objects.order_by('-submitted_at')[:10]

    return render(request, 'dashboard/dashboard.html', {
        # Stats
        'orders_today':    orders_today,
        'pending_orders':  pending_orders,
        'confirmed_orders': confirmed_orders,
        'total_revenue':   total_revenue,
        'new_requests':    new_requests,
        'low_stock':       low_stock,
        # Lists
        'orders_with_meta':  orders_with_meta,
        'custom_requests':   custom_requests,
        'status_choices':    STATUS_CHOICES,
        'today':             today,
    })


@staff_member_required(login_url='/login/')
@require_POST
def dashboard_update_status(request, order_id):
    """AJAX-style POST — update a single order's status from the dashboard."""
    order      = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get('status', '').strip()
    new_notes  = request.POST.get('notes', '').strip()

    valid_statuses = [s[0] for s in Order.STATUS_CHOICES]

    if new_status and new_status in valid_statuses:
        order.status = new_status
        order.notes  = new_notes
        order.save(update_fields=['status', 'notes'])
        messages.success(
            request,
            f'Order #{order.id} updated to "{order.get_status_display()}".'
        )
    else:
        messages.error(request, "Invalid status — order was not updated.")

    # Return to the dashboard, preserving any filter in the URL
    return redirect(request.POST.get('next', 'dashboard'))
