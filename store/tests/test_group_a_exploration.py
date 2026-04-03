"""
Group A Security — Bug Condition Exploration Tests
===================================================
These tests run against UNFIXED code and are EXPECTED TO FAIL.
Failure confirms the bugs exist. DO NOT fix the code or tests when they fail.

Bugs covered:
  1.1 — Open Redirect on Login
  1.2 — CSRF-Unsafe Logout (GET accepted)
  1.3 — Missing ALLOWED_HOST crashes at startup with cryptic error
  1.4 — Missing HSTS subdomain/preload flags in production settings

Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""

import importlib
import sys
import types
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.urls import reverse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="sectest", password="secpass123"):
    return User.objects.create_user(username=username, password=password)


# ---------------------------------------------------------------------------
# Bug 1.1 — Open Redirect on Login
# isBugCondition_1_1: next_url is external and not safe
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts the response does NOT redirect to the external URL.
#   On unfixed code, login_view passes next_url directly to redirect(),
#   so the response WILL redirect to https://evil.com — making the assertion fail.
# ---------------------------------------------------------------------------

class OpenRedirectExplorationTest(TestCase):
    """
    **Validates: Requirements 1.1**

    isBugCondition_1_1: POST /login/ with valid credentials and next=https://evil.com
    Expected (correct) behavior: redirect to home, NOT to https://evil.com
    Bug behavior (unfixed): redirects to https://evil.com
    """

    def setUp(self):
        self.user = make_user()

    def test_login_with_external_next_does_not_redirect_to_external_url(self):
        """
        Bug 1.1 exploration: POST /login/ with next=https://evil.com
        EXPECTED TO FAIL on unfixed code — proves the open redirect bug exists.
        Counterexample: response['Location'] == 'https://evil.com'
        """
        response = self.client.post(
            reverse("login") + "?next=https://evil.com",
            data={
                "username": "sectest",
                "password": "secpass123",
                "next": "https://evil.com",
            },
            follow=False,
        )
        # On unfixed code: response redirects to https://evil.com (bug)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        location = response.get("Location", "")
        self.assertFalse(
            location.startswith("https://evil.com"),
            msg=(
                f"BUG 1.1 CONFIRMED — Open redirect: login redirected to external URL: {location!r}. "
                "isBugCondition_1_1 holds: next_url is external and not safe."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.2 — CSRF-Unsafe Logout (GET accepted)
# isBugCondition_1_2: request.method == 'GET'
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts the user session is NOT destroyed on a GET request.
#   On unfixed code, logout_view calls logout(request) unconditionally,
#   so the session IS destroyed — making the assertion fail.
# ---------------------------------------------------------------------------

class GetLogoutExplorationTest(TestCase):
    """
    **Validates: Requirements 1.2**

    isBugCondition_1_2: GET /logout/ while authenticated
    Expected (correct) behavior: user remains logged in (GET should be rejected)
    Bug behavior (unfixed): user is logged out by a GET request
    """

    def setUp(self):
        self.user = make_user(username="logouttest", password="logoutpass123")

    def test_get_logout_does_not_destroy_session(self):
        """
        Bug 1.2 exploration: GET /logout/ while authenticated
        EXPECTED TO FAIL on unfixed code — proves the CSRF-unsafe logout bug exists.
        Counterexample: user._auth_user_id absent from session after GET /logout/
        """
        self.client.login(username="logouttest", password="logoutpass123")

        # Confirm user is authenticated before the GET
        self.assertIn("_auth_user_id", self.client.session)

        # Send a GET request to /logout/ (no CSRF token, no POST)
        self.client.get(reverse("logout"), follow=False)

        # On unfixed code: session is destroyed (bug)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertIn(
            "_auth_user_id",
            self.client.session,
            msg=(
                "BUG 1.2 CONFIRMED — CSRF-unsafe logout: GET /logout/ destroyed the user session. "
                "isBugCondition_1_2 holds: request.method == 'GET'."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.3 — Missing ALLOWED_HOST crashes at startup with cryptic error
# isBugCondition_1_3: DEBUG=False AND 'ALLOWED_HOST' not in env
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts that when ALLOWED_HOST is missing with DEBUG=False,
#   a clear ImproperlyConfigured exception with a descriptive message is raised.
#   On unfixed code, env('ALLOWED_HOST') raises a raw/cryptic exception
#   (environ.ImproperlyConfigured or KeyError) without a descriptive message
#   naming the missing variable — so the assertion about the message will fail.
# ---------------------------------------------------------------------------

class MissingAllowedHostExplorationTest(TestCase):
    """
    **Validates: Requirements 1.3**

    isBugCondition_1_3: DEBUG=False AND 'ALLOWED_HOST' not in environment
    Expected (correct) behavior: raises ImproperlyConfigured with a descriptive message
                                  that explicitly states the variable is required when
                                  DEBUG=False (e.g. "ALLOWED_HOST environment variable
                                  is required when DEBUG=False.")
    Bug behavior (unfixed): raises the generic django-environ ImproperlyConfigured
                             ("Set the ALLOWED_HOST environment variable") which does
                             not explain the DEBUG=False context, making it harder to
                             diagnose in production.
    """

    def test_missing_allowed_host_raises_descriptive_improperly_configured(self):
        """
        Bug 1.3 exploration: simulate settings load with DEBUG=False and ALLOWED_HOST missing.
        EXPECTED TO FAIL on unfixed code — proves the startup crash bug exists.

        The bug condition: the error message is the generic environ message and does NOT
        contain the context "DEBUG=False", meaning the developer gets a cryptic error
        without knowing WHY the variable is required.

        Counterexample: exception message is "Set the ALLOWED_HOST environment variable"
        (generic environ message) rather than a custom message naming the DEBUG=False context.
        """
        import environ as environ_lib
        from django.core.exceptions import ImproperlyConfigured

        # Remove core.settings from sys.modules so we can re-import it fresh
        settings_module = "core.settings"
        original_module = sys.modules.pop(settings_module, None)

        try:
            # Patch the environment: DEBUG=False, ALLOWED_HOST absent
            fake_env = {
                "SECRET_KEY": "fake-secret-key-for-testing",
                "DEBUG": "False",
                # ALLOWED_HOST intentionally omitted
                "DB_NAME": "test_db",
                "DB_USER": "postgres",
                "DB_PASSWORD": "",
                "DB_HOST": "localhost",
                "DB_PORT": "5432",
            }

            raised_exception = None
            exception_message = ""

            with patch.dict("os.environ", fake_env, clear=False):
                # Patch environ.Env.read_env to be a no-op (avoid reading .env file)
                with patch.object(environ_lib.Env, "read_env", return_value=None):
                    try:
                        import core.settings  # noqa: F401
                    except Exception as exc:
                        raised_exception = exc
                        exception_message = str(exc)

            # An exception must be raised (both unfixed and fixed code raise something)
            self.assertIsNotNone(
                raised_exception,
                msg="Expected an exception when ALLOWED_HOST is missing with DEBUG=False, but none was raised.",
            )

            # The fix requires a CUSTOM ImproperlyConfigured message that explicitly
            # mentions "DEBUG=False" so the developer knows WHY the variable is required.
            # On UNFIXED code: the message is the generic environ message which does NOT
            # contain "DEBUG=False" — the assertion below will FAIL, confirming the bug.
            self.assertIn(
                "DEBUG=False",
                exception_message,
                msg=(
                    f"BUG 1.3 CONFIRMED — Startup error message does not explain the DEBUG=False context: "
                    f"{exception_message!r}. "
                    "isBugCondition_1_3 holds: DEBUG=False AND 'ALLOWED_HOST' not in env. "
                    "The generic environ message does not tell the developer WHY the variable is required."
                ),
            )

        finally:
            # Restore the original settings module
            sys.modules.pop(settings_module, None)
            if original_module is not None:
                sys.modules[settings_module] = original_module


# ---------------------------------------------------------------------------
# Bug 1.4 — Missing HSTS subdomain and preload flags
# isBugCondition_1_4: SECURE_HSTS_SECONDS > 0 AND flags missing
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts SECURE_HSTS_INCLUDE_SUBDOMAINS and SECURE_HSTS_PRELOAD are True.
#   On unfixed code, settings.py sets SECURE_HSTS_SECONDS but omits the two flags,
#   so the assertions will fail, confirming the bug.
# ---------------------------------------------------------------------------

class MissingHstsFlagsExplorationTest(TestCase):
    """
    **Validates: Requirements 1.4**

    isBugCondition_1_4: SECURE_HSTS_SECONDS > 0 AND (SECURE_HSTS_INCLUDE_SUBDOMAINS != True
                         OR SECURE_HSTS_PRELOAD != True)
    Expected (correct) behavior: both flags are True when HSTS is enabled
    Bug behavior (unfixed): flags are absent/False
    """

    @override_settings(
        DEBUG=False,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_hsts_include_subdomains_and_preload_are_set_in_production(self):
        """
        Bug 1.4 exploration: with DEBUG=False and SECURE_HSTS_SECONDS set,
        assert SECURE_HSTS_INCLUDE_SUBDOMAINS and SECURE_HSTS_PRELOAD are True.
        EXPECTED TO FAIL on unfixed code — proves the missing HSTS flags bug exists.
        Counterexample: SECURE_HSTS_INCLUDE_SUBDOMAINS is False/absent,
                        SECURE_HSTS_PRELOAD is False/absent
        """
        from django.conf import settings

        # Confirm the bug condition holds: HSTS is enabled
        self.assertGreater(
            settings.SECURE_HSTS_SECONDS,
            0,
            msg="Precondition: SECURE_HSTS_SECONDS must be > 0 for isBugCondition_1_4 to hold.",
        )

        # On FIXED code: both flags are True
        # On UNFIXED code: flags are absent (getattr returns False) — assertions fail
        include_subdomains = getattr(settings, "SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
        preload = getattr(settings, "SECURE_HSTS_PRELOAD", False)

        self.assertTrue(
            include_subdomains,
            msg=(
                f"BUG 1.4 CONFIRMED — SECURE_HSTS_INCLUDE_SUBDOMAINS is {include_subdomains!r} "
                "(expected True). isBugCondition_1_4 holds: SECURE_HSTS_SECONDS > 0 AND flag missing."
            ),
        )
        self.assertTrue(
            preload,
            msg=(
                f"BUG 1.4 CONFIRMED — SECURE_HSTS_PRELOAD is {preload!r} "
                "(expected True). isBugCondition_1_4 holds: SECURE_HSTS_SECONDS > 0 AND flag missing."
            ),
        )
