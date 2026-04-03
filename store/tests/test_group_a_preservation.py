"""
Group A Security — Preservation Tests
======================================
These tests run against UNFIXED code and are EXPECTED TO PASS.
They document baseline behavior for non-buggy inputs that must be preserved
after fixes are applied.

Bugs covered:
  1.1 — Valid internal next URL continues to redirect correctly
  1.2 — POST logout with valid CSRF token continues to work
  1.3 — Settings load normally when ALLOWED_HOST is present (DEBUG=False)
  1.4 — DEBUG=True path is unaffected by HSTS block

Validates: Requirements 3.1, 3.2
"""

import importlib
import sys

from unittest.mock import patch

import environ as environ_lib

from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.urls import reverse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="preserve_user", password="preservepass123"):
    return User.objects.create_user(username=username, password=password)


# ---------------------------------------------------------------------------
# Bug 1.1 Preservation — Valid internal next URL redirects correctly
# isBugCondition_1_1 returns false: next_url is a safe internal path
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class InternalNextRedirectPreservationTest(TestCase):
    """
    **Validates: Requirements 3.1**

    Preservation: POST /login/ with next=/orders/ (safe internal path)
    Expected behavior: redirect to /orders/ after successful authentication.
    isBugCondition_1_1 returns false because next_url is internal and safe.
    """

    def setUp(self):
        self.user = make_user(username="pres_login", password="prespass123")

    def test_login_with_internal_next_redirects_to_internal_url(self):
        """
        Preservation 1.1: POST /login/ with next=/orders/ should redirect to /orders/.
        This must continue to work after the open-redirect fix is applied.
        """
        response = self.client.post(
            reverse("login") + "?next=/orders/",
            data={
                "username": "pres_login",
                "password": "prespass123",
                "next": "/orders/",
            },
            follow=False,
        )
        # Should be a redirect (302)
        self.assertIn(response.status_code, [301, 302],
                      msg="Expected a redirect after login with internal next URL.")
        location = response.get("Location", "")
        self.assertEqual(
            location, "/orders/",
            msg=(
                f"Preservation 1.1 FAILED — login with internal next=/orders/ "
                f"redirected to {location!r} instead of '/orders/'."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.2 Preservation — POST logout with valid CSRF token still works
# isBugCondition_1_2 returns false: request.method == 'POST'
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class PostLogoutPreservationTest(TestCase):
    """
    **Validates: Requirements 3.2**

    Preservation: POST /logout/ with valid CSRF token logs user out and redirects to home.
    isBugCondition_1_2 returns false because request.method == 'POST'.
    """

    def setUp(self):
        self.user = make_user(username="pres_logout", password="logoutpres123")

    def test_post_logout_logs_out_and_redirects_to_home(self):
        """
        Preservation 1.2: POST /logout/ should log the user out and redirect to home.
        This must continue to work after the @require_POST fix is applied.

        Note: on unfixed code, logout_view accepts any method and always logs out,
        so a POST also works — this is the preserved behavior.
        """
        self.client.login(username="pres_logout", password="logoutpres123")
        self.assertIn("_auth_user_id", self.client.session,
                      msg="Precondition: user must be logged in before testing POST logout.")

        response = self.client.post(reverse("logout"), follow=False)

        # User should be logged out
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
            msg="Preservation 1.2 FAILED — POST /logout/ did not destroy the user session.",
        )
        # Should redirect (to home)
        self.assertIn(response.status_code, [301, 302],
                      msg="Preservation 1.2 FAILED — POST /logout/ did not redirect.")


# ---------------------------------------------------------------------------
# Bug 1.3 Preservation — Settings load normally when ALLOWED_HOST is present
# isBugCondition_1_3 returns false: DEBUG=False AND 'ALLOWED_HOST' IS in env
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class AllowedHostPresentPreservationTest(TestCase):
    """
    **Validates: Requirements 3.1 (startup preservation)**

    Preservation: With DEBUG=False and ALLOWED_HOST=mysite.com present,
    settings load without raising any exception.
    isBugCondition_1_3 returns false because ALLOWED_HOST is present.
    """

    def test_settings_load_normally_when_allowed_host_is_present(self):
        """
        Preservation 1.3: When ALLOWED_HOST is set with DEBUG=False, no exception is raised.
        This must continue to work after the startup-crash fix is applied.
        """
        settings_module = "core.settings"
        original_module = sys.modules.pop(settings_module, None)

        try:
            fake_env = {
                "SECRET_KEY": "fake-secret-key-for-testing",
                "DEBUG": "False",
                "ALLOWED_HOST": "mysite.com",
                "DB_NAME": "test_db",
                "DB_USER": "postgres",
                "DB_PASSWORD": "",
                "DB_HOST": "localhost",
                "DB_PORT": "5432",
            }

            raised_exception = None

            with patch.dict("os.environ", fake_env, clear=False):
                with patch.object(environ_lib.Env, "read_env", return_value=None):
                    try:
                        import core.settings  # noqa: F401
                    except Exception as exc:
                        raised_exception = exc

            self.assertIsNone(
                raised_exception,
                msg=(
                    f"Preservation 1.3 FAILED — settings raised an exception even though "
                    f"ALLOWED_HOST is present: {raised_exception!r}"
                ),
            )

        finally:
            sys.modules.pop(settings_module, None)
            if original_module is not None:
                sys.modules[settings_module] = original_module


# ---------------------------------------------------------------------------
# Bug 1.4 Preservation — DEBUG=True path is unaffected by HSTS block
# isBugCondition_1_4 returns false: DEBUG=True means HSTS block is not entered
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class DebugModeHstsPreservationTest(TestCase):
    """
    **Validates: Requirements 3.1 (dev settings preservation)**

    Preservation: With DEBUG=True, the HSTS security block is not entered,
    so SECURE_HSTS_SECONDS, SECURE_HSTS_INCLUDE_SUBDOMAINS, and SECURE_HSTS_PRELOAD
    are not set (or remain at their defaults).
    isBugCondition_1_4 returns false because DEBUG=True.
    """

    @override_settings(DEBUG=True)
    def test_debug_mode_does_not_set_hsts_settings(self):
        """
        Preservation 1.4: With DEBUG=True, HSTS settings should not be forced on.
        The production security block is guarded by `if not DEBUG:`, so dev settings
        are unaffected. This must remain true after the HSTS flags fix is applied.
        """
        from django.conf import settings

        # In DEBUG=True mode, the production security block is not entered.
        # SECURE_HSTS_SECONDS should not be set (or be 0/absent).
        hsts_seconds = getattr(settings, "SECURE_HSTS_SECONDS", 0)
        self.assertEqual(
            hsts_seconds, 0,
            msg=(
                f"Preservation 1.4 FAILED — SECURE_HSTS_SECONDS is {hsts_seconds!r} "
                "in DEBUG=True mode; the HSTS block should not be entered."
            ),
        )

        # SECURE_HSTS_INCLUDE_SUBDOMAINS and SECURE_HSTS_PRELOAD should not be True
        # in DEBUG mode (they are only set in the production block).
        include_subdomains = getattr(settings, "SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
        preload = getattr(settings, "SECURE_HSTS_PRELOAD", False)

        self.assertFalse(
            include_subdomains,
            msg=(
                f"Preservation 1.4 FAILED — SECURE_HSTS_INCLUDE_SUBDOMAINS is {include_subdomains!r} "
                "in DEBUG=True mode; dev settings should be unaffected."
            ),
        )
        self.assertFalse(
            preload,
            msg=(
                f"Preservation 1.4 FAILED — SECURE_HSTS_PRELOAD is {preload!r} "
                "in DEBUG=True mode; dev settings should be unaffected."
            ),
        )
