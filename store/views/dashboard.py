"""
Owner Dashboard — /dashboard/
Staff-only pages for managing the store without touching Django admin.

Pages:
  /dashboard/                     — main overview
  /dashboard/stock/               — stock manager
  /dashboard/products/            — product quick-edit
  /dashboard/guide/               — how-to guide
  /dashboard/export/orders.csv    — CSV export
"""
import csv
from itertools import groupby

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.timezone import now

from store.models import Order, CustomRequest, Product, Category


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────
STATUS_META = {
    'PENDING':   {'label': '⏳ Pending',          'bg': 'bg-amber-100',  'text': 'text-amber-800'},
    'CONFIRMED': {'label': '✅ Confirmed',         'bg': 'bg-blue-100',   'text': 'text-blue-800'},
    'SHIPPED':   {'label': '🚚 Out for Delivery',  'bg': 'bg-purple-100', 'text': 'text-purple-800'},
    'DELIVERED': {'label': '🎉 Delivered',         'bg': 'bg-green-100',  'text': 'text-green-800'},
    'REJECTED':  {'label': '❌ Rejected',          'bg': 'bg-red-100',    'text': 'text-red-800'},
}

STATUS_CHOICES = [
    ('PENDING',   '⏳ Pending'),
    ('CONFIRMED', '✅ Confirmed'),
    ('SHIPPED',   '🚚 Out for Delivery'),
    ('DELIVERED', '🎉 Delivered'),
    ('REJECTED',  '❌ Rejected'),
]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DASHBOARD  —  /dashboard/
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='/login/')
def dashboard(request):
    today = now().date()

    orders_today     = Order.objects.filter(created_at__date=today).count()
    pending_orders   = Order.objects.filter(status='PENDING').count()
    confirmed_orders = Order.objects.filter(status='CONFIRMED').count()
    total_revenue    = sum(
        o.total_amount for o in Order.objects.filter(status='DELIVERED')
    )
    new_requests = CustomRequest.objects.filter(submitted_at__date=today).count()
    low_stock    = Product.objects.filter(is_active=True, stock__lte=3).order_by('stock')

    recent_orders = (
        Order.objects
        .select_related('user')
        .prefetch_related('items__product')
        .order_by('-created_at')[:20]
    )
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

    custom_requests = CustomRequest.objects.order_by('-submitted_at')[:10]

    return render(request, 'dashboard/dashboard.html', {
        'orders_today':      orders_today,
        'pending_orders':    pending_orders,
        'confirmed_orders':  confirmed_orders,
        'total_revenue':     total_revenue,
        'new_requests':      new_requests,
        'low_stock':         low_stock,
        'orders_with_meta':  orders_with_meta,
        'custom_requests':   custom_requests,
        'status_choices':    STATUS_CHOICES,
        'today':             today,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ORDER STATUS + NOTES UPDATE
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='/login/')
@require_POST
def dashboard_update_status(request, order_id):
    order      = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get('status', '').strip()
    new_notes  = request.POST.get('notes', '').strip()
    valid      = [s[0] for s in Order.STATUS_CHOICES]

    if new_status and new_status in valid:
        order.status = new_status
        order.notes  = new_notes
        order.save(update_fields=['status', 'notes'])
        messages.success(request, f'Order #{order.id} updated to "{order.get_status_display()}".')
    else:
        messages.error(request, 'Invalid status — order was not updated.')

    return redirect(request.POST.get('next', 'dashboard'))


# ─────────────────────────────────────────────────────────────────────────────
# STOCK MANAGER  —  /dashboard/stock/
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='/login/')
def dashboard_stock(request):
    products = (
        Product.objects
        .filter(is_active=True)
        .select_related('category')
        .order_by('category__name', 'name')
    )
    grouped = []
    for cat_name, prods in groupby(products, key=lambda p: p.category.name):
        grouped.append((cat_name, list(prods)))

    return render(request, 'dashboard/stock.html', {
        'grouped':      grouped,
        'out_of_stock': Product.objects.filter(is_active=True, stock=0).count(),
        'low_stock':    Product.objects.filter(is_active=True, stock__gt=0, stock__lte=3).count(),
        'total_active': Product.objects.filter(is_active=True).count(),
    })


@staff_member_required(login_url='/login/')
@require_POST
def dashboard_update_stock(request, product_id):
    product   = get_object_or_404(Product, pk=product_id)
    raw_stock = request.POST.get('stock', '').strip()
    try:
        new_stock = int(raw_stock)
        if new_stock < 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, f'"{raw_stock}" is not a valid stock number.')
        return redirect('dashboard_stock')

    old_stock     = product.stock
    product.stock = new_stock
    product.save(update_fields=['stock'])

    if new_stock == 0:
        messages.warning(request, f'"{product.name}" is now out of stock.')
    elif new_stock <= 3:
        messages.warning(request, f'"{product.name}" updated to {new_stock} — still low stock.')
    else:
        messages.success(request, f'"{product.name}" stock updated: {old_stock} → {new_stock}.')

    return redirect(request.POST.get('next', 'dashboard_stock'))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — CSV EXPORT  —  /dashboard/export/orders.csv
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='/login/')
def export_orders_csv(request):
    """
    Download all orders as a CSV file.
    Optional GET params:
      ?status=PENDING   — filter by status
      ?from=2024-01-01  — filter from date (YYYY-MM-DD)
      ?to=2024-12-31    — filter to date (YYYY-MM-DD)
    """
    qs = Order.objects.prefetch_related('items__product').order_by('-created_at')

    # Apply optional filters
    status_filter = request.GET.get('status', '').strip().upper()
    from_date     = request.GET.get('from', '').strip()
    to_date       = request.GET.get('to', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if from_date:
        try:
            qs = qs.filter(created_at__date__gte=from_date)
        except Exception:
            pass
    if to_date:
        try:
            qs = qs.filter(created_at__date__lte=to_date)
        except Exception:
            pass

    # Build the HTTP response with CSV content type
    filename = f"happy-heavens-orders-{now().strftime('%Y-%m-%d')}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Write BOM so Excel opens it correctly with Indian characters
    response.write('\ufeff')

    writer = csv.writer(response)

    # Header row
    writer.writerow([
        'Order #',
        'Date',
        'Customer Name',
        'Phone',
        'Email',
        'Address',
        'City',
        'Pincode',
        'Items',
        'Total (₹)',
        'Payment Method',
        'Status',
        'Notes',
    ])

    # Data rows
    for order in qs:
        items_text = ' | '.join(
            f"{item.quantity}x {item.product.name if item.product else 'Deleted'} @ ₹{item.price}"
            for item in order.items.all()
        )
        writer.writerow([
            f'#{order.id}',
            order.created_at.strftime('%d %b %Y %I:%M %p'),
            order.full_name,
            order.phone_number,
            order.user.email or '—',
            order.address.replace('\n', ' '),
            order.city,
            order.pincode,
            items_text,
            order.total_amount,
            order.get_payment_method_display(),
            order.get_status_display(),
            order.notes or '—',
        ])

    return response


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — PRODUCT QUICK-EDIT  —  /dashboard/products/
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='/login/')
def dashboard_products(request):
    """
    List all products with quick inline edit for name, price,
    description, category, visibility, and stock.
    """
    products   = (
        Product.objects
        .select_related('category')
        .order_by('category__name', 'name')
    )
    categories = Category.objects.order_by('name')

    return render(request, 'dashboard/products.html', {
        'products':   products,
        'categories': categories,
    })


@staff_member_required(login_url='/login/')
@require_POST
def dashboard_update_product(request, product_id):
    """Save quick-edit changes for a single product."""
    product = get_object_or_404(Product, pk=product_id)

    name        = request.POST.get('name', '').strip()
    price_raw   = request.POST.get('price', '').strip()
    stock_raw   = request.POST.get('stock', '').strip()
    description = request.POST.get('description', '').strip()
    category_id = request.POST.get('category', '').strip()
    is_active   = request.POST.get('is_active') == 'on'

    errors = []

    if not name:
        errors.append('Product name cannot be empty.')

    try:
        price = float(price_raw)
        if price < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append(f'"{price_raw}" is not a valid price.')
        price = None

    try:
        stock = int(stock_raw)
        if stock < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append(f'"{stock_raw}" is not a valid stock number.')
        stock = None

    category = None
    if category_id:
        try:
            category = Category.objects.get(pk=int(category_id))
        except (Category.DoesNotExist, ValueError):
            errors.append('Selected category does not exist.')

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect('dashboard_products')

    product.name        = name
    product.price       = price
    product.stock       = stock
    product.description = description
    product.is_active   = is_active
    if category:
        product.category = category
    product.save(update_fields=['name', 'price', 'stock', 'description', 'is_active', 'category'])

    messages.success(request, f'"{product.name}" saved successfully.')
    return redirect(request.POST.get('next', 'dashboard_products'))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — HOW-TO GUIDE  —  /dashboard/guide/
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='/login/')
def dashboard_guide(request):
    """Plain-language guide for the store owner."""
    return render(request, 'dashboard/guide.html')
