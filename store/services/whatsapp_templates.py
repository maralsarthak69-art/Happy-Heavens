"""
WhatsApp message templates for different notification types.
"""
from store.models import Order


def format_new_order_message(order: Order) -> str:
    """Format message for new order notification to admin."""
    items = order.items.select_related('product').all()
    items_text = "\n".join([
        f"  • {item.product.name if item.product else 'Deleted Product'} x{item.quantity} - ₹{item.price}"
        for item in items
    ])

    payment_method = dict(Order.PAYMENT_METHODS).get(order.payment_method, order.payment_method)
    
    message = f"""🔔 *NEW ORDER RECEIVED!*

📦 *Order #{order.id}*
👤 Customer: {order.full_name}
📱 Phone: {order.phone_number}

🛍️ *Items:*
{items_text}

💰 *Total: ₹{order.total_amount}*
💳 Payment: {payment_method}

📍 *Delivery Address:*
{order.address}
{order.city}, {order.pincode}

⏰ Ordered at: {order.created_at.strftime('%d %b %Y, %I:%M %p')}

{"📸 Payment screenshot uploaded!" if order.payment_screenshot else ""}

🔗 Check admin panel to verify and confirm the order."""

    return message


def format_order_status_update(order: Order, old_status: str, new_status: str) -> str:
    """Format message for order status update to customer."""
    status_emojis = {
        'PENDING': '⏳',
        'CONFIRMED': '✅',
        'SHIPPED': '🚚',
        'DELIVERED': '🎉',
        'REJECTED': '❌'
    }
    
    status_messages = {
        'CONFIRMED': 'Your order has been confirmed and is being prepared!',
        'SHIPPED': 'Your order is out for delivery!',
        'DELIVERED': 'Your order has been delivered. Thank you for shopping with us!',
        'REJECTED': 'Unfortunately, we could not process your order. Please contact us for details.'
    }
    
    emoji = status_emojis.get(new_status, '📦')
    status_text = dict(Order.STATUS_CHOICES).get(new_status, new_status)
    custom_message = status_messages.get(new_status, 'Your order status has been updated.')
    
    message = f"""{emoji} *ORDER UPDATE*

Hi {order.full_name}!

{custom_message}

📦 Order #{order.id}
Status: {status_text}
Total: ₹{order.total_amount}

Track your order: [Your website URL]/orders/{order.id}/

Questions? Reply to this message or call us!

- Happy Heavens Team 🌸"""

    return message
