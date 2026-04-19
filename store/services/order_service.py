"""
OrderService — all order creation and stock management logic lives here.
Views call this service; they never touch stock or Order creation directly.
This makes it trivial to add coupons, loyalty points, or a new payment
method later without touching views.
"""
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404

from store.models import Order, OrderItem, Product
from store.exceptions import InsufficientStockError
from store.services.whatsapp_service import notify_admin_new_order

logger = logging.getLogger(__name__)


def create_order(*, user, form_data: dict, cart_items: list, total, payment_screenshot=None) -> Order:
    """
    Atomically validate stock, decrement inventory, create the Order and
    all OrderItems, then return the saved Order instance.

    Raises InsufficientStockError if any item exceeds available stock.
    All DB writes are wrapped in a single transaction — nothing is persisted
    on failure.

    Args:
        user:               The authenticated User placing the order.
        form_data:          Cleaned data dict from CheckoutForm.
        cart_items:         Snapshot list from list(cart) — already hydrated.
        total:              Decimal total price from cart.get_total_price().
        payment_screenshot: Uploaded file object or None.

    Returns:
        The newly created Order instance.
    """
    with transaction.atomic():
        # --- 1. Validate & decrement stock atomically ---
        for item in cart_items:
            product = get_object_or_404(
                Product.objects.select_for_update(), pk=item['product'].pk
            )
            if product.stock < item['quantity']:
                raise InsufficientStockError(product)
            product.stock -= item['quantity']
            product.save(update_fields=['stock'])

        # --- 2. Create the Order record ---
        order = Order.objects.create(
            user=user,
            full_name=form_data['full_name'],
            phone_number=form_data['phone_number'],
            address=form_data['address'],
            city=form_data['city'],
            pincode=form_data['pincode'],
            payment_method=form_data['payment_method'],
            payment_screenshot=payment_screenshot,
            total_amount=total,
        )

        # --- 3. Create OrderItems with price locked at purchase time ---
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['price'],
            )
            for item in cart_items
        ])

    # --- 4. Send WhatsApp notification to admin (outside transaction) ---
    try:
        notify_admin_new_order(order)
    except Exception as e:
        # Log but don't fail the order if notification fails
        logger.error(f"Failed to send WhatsApp notification for Order #{order.id}: {e}")

    return order
