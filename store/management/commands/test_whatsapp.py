"""
Management command to test WhatsApp notification integration.
Usage: python manage.py test_whatsapp
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from store.services.whatsapp_service import whatsapp_service


class Command(BaseCommand):
    help = 'Test WhatsApp notification service configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Testing WhatsApp Configuration...\n'))

        # Check configuration
        if not whatsapp_service.is_configured():
            self.stdout.write(self.style.ERROR('❌ WhatsApp service is NOT configured properly.\n'))
            self.stdout.write('Please check the following environment variables:')
            self.stdout.write(f'  TWILIO_ACCOUNT_SID: {"✓" if settings.TWILIO_ACCOUNT_SID else "✗ Missing"}')
            self.stdout.write(f'  TWILIO_AUTH_TOKEN: {"✓" if settings.TWILIO_AUTH_TOKEN else "✗ Missing"}')
            self.stdout.write(f'  TWILIO_WHATSAPP_FROM: {"✓" if settings.TWILIO_WHATSAPP_FROM else "✗ Missing"}')
            self.stdout.write(f'  ADMIN_WHATSAPP_NUMBER: {"✓" if settings.ADMIN_WHATSAPP_NUMBER else "✗ Missing"}')
            self.stdout.write('\nRefer to WHATSAPP_SETUP.md for setup instructions.')
            return

        self.stdout.write(self.style.SUCCESS('✓ Configuration looks good!\n'))
        self.stdout.write(f'From: {settings.TWILIO_WHATSAPP_FROM}')
        self.stdout.write(f'To: {settings.ADMIN_WHATSAPP_NUMBER}\n')

        # Send test message
        self.stdout.write('Sending test message...')
        
        try:
            message = whatsapp_service.client.messages.create(
                from_=settings.TWILIO_WHATSAPP_FROM,
                body='🎉 Test message from Happy Heavens!\n\nYour WhatsApp notification system is working correctly. You will receive order notifications here.',
                to=settings.ADMIN_WHATSAPP_NUMBER
            )
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Test message sent successfully!'))
            self.stdout.write(f'Message SID: {message.sid}')
            self.stdout.write(f'Status: {message.status}')
            self.stdout.write('\nCheck your WhatsApp to confirm receipt.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Failed to send test message:'))
            self.stdout.write(str(e))
            self.stdout.write('\nCommon issues:')
            self.stdout.write('  1. Admin number not joined to Twilio sandbox')
            self.stdout.write('  2. Invalid credentials')
            self.stdout.write('  3. Incorrect phone number format')
            self.stdout.write('\nRefer to WHATSAPP_SETUP.md for troubleshooting.')
