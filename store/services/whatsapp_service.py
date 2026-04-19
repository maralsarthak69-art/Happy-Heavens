"""
WhatsApp Notification Service using Twilio WhatsApp API.
Sends order notifications to admin when new orders are placed.
"""
import logging
from typing import Optional

from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from store.models import Order
from store.services.whatsapp_templates import (
    format_new_order_message,
    format_order_status_update
)

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Handles WhatsApp notifications via Twilio API."""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM
        self.admin_number = settings.ADMIN_WHATSAPP_NUMBER
        self.client = None

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)

    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured."""
        return all([
            self.account_sid,
            self.auth_token,
            self.from_number,
            self.admin_number,
            self.client
        ])

    def send_new_order_notification(self, order: Order) -> bool:
        """
        Send WhatsApp notification to admin about a new order.

        Args:
            order: The Order instance that was just created.

        Returns:
            True if notification was sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.warning("WhatsApp service not configured. Skipping notification.")
            return False

        try:
            message_body = format_new_order_message(order)
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=self.admin_number
            )

            logger.info(f"WhatsApp notification sent for Order #{order.id}. SID: {message.sid}")
            return True

        except TwilioRestException as e:
            logger.error(f"Failed to send WhatsApp notification for Order #{order.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp notification: {e}")
            return False

    def send_order_status_update(self, order: Order, old_status: str, new_status: str) -> bool:
        """
        Send WhatsApp notification to customer about order status change.

        Args:
            order: The Order instance.
            old_status: Previous status.
            new_status: New status.

        Returns:
            True if notification was sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.warning("WhatsApp service not configured. Skipping notification.")
            return False

        # Format customer phone number for WhatsApp
        customer_number = order.phone_number
        if not customer_number.startswith('whatsapp:'):
            # Add country code if not present (assuming India +91)
            if not customer_number.startswith('+'):
                customer_number = f'+91{customer_number}'
            customer_number = f'whatsapp:{customer_number}'

        try:
            message_body = format_order_status_update(order, old_status, new_status)
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=customer_number
            )

            logger.info(f"Status update sent to customer for Order #{order.id}. SID: {message.sid}")
            return True

        except TwilioRestException as e:
            logger.error(f"Failed to send status update for Order #{order.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending status update: {e}")
            return False


# Singleton instance
whatsapp_service = WhatsAppService()


def notify_admin_new_order(order: Order) -> bool:
    """
    Convenience function to send new order notification to admin.

    Args:
        order: The Order instance.

    Returns:
        True if notification sent successfully, False otherwise.
    """
    return whatsapp_service.send_new_order_notification(order)


def notify_customer_status_update(order: Order, old_status: str, new_status: str) -> bool:
    """
    Convenience function to send order status update to customer.

    Args:
        order: The Order instance.
        old_status: Previous status.
        new_status: New status.

    Returns:
        True if notification sent successfully, False otherwise.
    """
    return whatsapp_service.send_order_status_update(order, old_status, new_status)
