"""
Newsletter subscription view.
Accepts POST with an email address, validates it, and returns a success redirect.
"""
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email', '').strip()
    try:
        validate_email(email)
        # TODO: persist subscription (e.g. NewsletterSubscriber model or third-party service)
        messages.success(request, 'Thanks for subscribing! We\'ll be in touch.')
    except ValidationError:
        messages.error(request, 'Please enter a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))
