import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class AdminSessionTimeoutMiddleware:
    """
    Logs out staff/superusers after ADMIN_SESSION_TIMEOUT seconds of inactivity.
    Regular customers are unaffected.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'ADMIN_SESSION_TIMEOUT', 60 * 60 * 2)

    def __call__(self, request):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            last_activity = request.session.get('admin_last_activity')
            now = int(time.time())

            if last_activity and (now - last_activity) > self.timeout:
                logout(request)
                return redirect(f'/admin/login/?next={request.path}')

            request.session['admin_last_activity'] = now

        return self.get_response(request)
