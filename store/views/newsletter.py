from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from store.models import NewsletterSubscriber


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email', '').strip()
    try:
        validate_email(email)
        _, created = NewsletterSubscriber.objects.get_or_create(email=email)
        if created:
            messages.success(request, "Thanks for subscribing! We'll be in touch.")
        else:
            messages.info(request, "You're already subscribed.")
    except ValidationError:
        messages.error(request, 'Please enter a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))
