from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from .models import Order, CustomRequest, Category, Product
import logging

logger = logging.getLogger(__name__)


# Track previous status to detect changes
@receiver(pre_save, sender=Order)
def capture_previous_order_status(sender, instance, **kwargs):
    """Store the previous status on the instance before saving."""
    if instance.pk:
        try:
            instance._previous_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def notify_customer_on_status_change(sender, instance, created, **kwargs):
    """Send email and WhatsApp to customer when Order status changes."""
    previous_status = getattr(instance, '_previous_status', None)

    # Only notify on status change — not on creation, not when status is unchanged
    if not created and previous_status is not None and previous_status != instance.status:
        # Send email notification
        customer_email = instance.user.email
        if customer_email:
            subject = f"Happy Heavens — Order #{instance.id} Status Update"
            message = (
                f"Hi {instance.full_name},\n\n"
                f"Your order #{instance.id} has been updated.\n"
                f"New status: {instance.get_status_display()}\n\n"
                f"Thank you for shopping with Happy Heavens!"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer_email],
                fail_silently=True,
            )
        
        # Send WhatsApp notification to customer
        try:
            from store.services.whatsapp_service import notify_customer_status_update
            notify_customer_status_update(instance, previous_status, instance.status)
        except Exception as e:
            logger.error(f"Failed to send WhatsApp status update for Order #{instance.id}: {e}")


@receiver(post_save, sender=CustomRequest)
def notify_owner_on_custom_request(sender, instance, created, **kwargs):
    """Send email alert to store owner when a CustomRequest is submitted."""
    if not created:
        return

    owner_email = getattr(settings, 'STORE_OWNER_EMAIL', None)
    if not owner_email:
        return

    subject = f"Happy Heavens — New Custom Request from {instance.name}"
    message = (
        f"A new custom request has been submitted.\n\n"
        f"Customer Name: {instance.name}\n"
        f"Phone Number: {instance.phone_number}\n"
        f"Idea Description:\n{instance.idea_description}\n\n"
        f"Submitted at: {instance.submitted_at}"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[owner_email],
        fail_silently=True,
    )


# ---------------------------------------------------------------------------
# Cache invalidation — bust nav_categories whenever a Category or Product
# is saved so the navbar reflects changes within one request cycle.
# ---------------------------------------------------------------------------
@receiver(post_save, sender=Category)
def invalidate_category_cache_on_category_save(sender, **kwargs):
    cache.delete('nav_categories')


@receiver(post_save, sender=Product)
def invalidate_category_cache_on_product_save(sender, **kwargs):
    cache.delete('nav_categories')
