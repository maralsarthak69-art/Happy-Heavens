from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import order

@receiver(post_save, sender=order)
def update_stock_on_approval(sender, instance, **kwargs):
    """
    Automatically subtracts product stock when an order 
    is marked as 'Approved' by Sarthak.
    """
    # We only trigger this if the status is flipped to 'Approved'
    if instance.status == 'Approved':
        for item in instance.items.all(): # 'items' is the related_name for OrderItem
            product = item.product
            # Check if stock exists to prevent negative numbers
            if product.stock >= item.quantity:
                product.stock -= item.quantity
                product.save()