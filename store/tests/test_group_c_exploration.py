"""
Group C Data Integrity / UX — Bug Condition Exploration Tests
=============================================================
These tests run against UNFIXED code and are EXPECTED TO FAIL.
Failure confirms the bugs exist. DO NOT fix the code or tests when they fail.

Bugs covered:
  1.8  — Missing Email Silences Order Notifications (email not required on signup)
  1.9  — Inactive Product Slug Leaked via Redirect (302 instead of 404)
  1.10 — Broken Password Reset Link (href="#" in login template)
  1.11 — Non-functional Newsletter Form (no <form> element in footer)

Validates: Requirements 1.8, 1.9, 1.10, 1.11
"""

import os

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from store.forms import SignUpForm
from store.models import Category, Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category():
    return Category.objects.create(name="Test Category", slug="test-category-c")


def make_product(category, name="Test Product", slug="test-product-c", stock=5, is_active=True):
    return Product.objects.create(
        category=category,
        name=name,
        slug=slug,
        price="10.00",
        stock=stock,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# Bug 1.8 — Missing Email Silences Order Notifications
# isBugCondition_1_8: input.email IS NULL OR input.email == ''
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts that SignUpForm with email='' is INVALID (form should reject it).
#   On unfixed code, SignUpForm does not require email, so the form IS valid and
#   the user is created — making the assertion fail.
# ---------------------------------------------------------------------------

class MissingEmailExplorationTest(TestCase):
    """
    **Validates: Requirements 1.8**

    isBugCondition_1_8: email is null or empty on signup form submission
    Expected (correct) behavior: SignUpForm rejects submission with a validation error
    Bug behavior (unfixed): form is valid and user is created with empty email
    """

    def test_signup_form_with_empty_email_is_invalid(self):
        """
        Bug 1.8 exploration: submit SignUpForm with email=''.
        EXPECTED TO FAIL on unfixed code — proves the missing email validation bug exists.
        Counterexample: form.is_valid() == True and user is created with empty email
        """
        form_data = {
            "username": "testuser_noemail",
            "email": "",
            "first_name": "Test",
            "last_name": "User",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignUpForm(data=form_data)

        # On unfixed code: form.is_valid() == True (bug confirmed — email not required)
        # On fixed code: form.is_valid() == False (email field is required)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertFalse(
            form.is_valid(),
            msg=(
                "BUG 1.8 CONFIRMED — Missing email validation: SignUpForm accepted an empty "
                "email address and is_valid() returned True. "
                "isBugCondition_1_8 holds: email is null or empty. "
                "SignUpForm does not set email field as required, so users can register "
                "without an email, silencing all order notification emails."
            ),
        )

    def test_signup_with_empty_email_does_not_create_user(self):
        """
        Bug 1.8 exploration: POST to /signup/ with email=''.
        EXPECTED TO FAIL on unfixed code — user should NOT be created without email.
        Counterexample: User.objects.filter(username='testuser_noemail2').exists() == True
        """
        initial_count = User.objects.count()

        self.client.post(
            reverse("signup"),
            data={
                "username": "testuser_noemail2",
                "email": "",
                "first_name": "Test",
                "last_name": "User",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        # On unfixed code: user IS created (bug confirmed)
        # On fixed code: user is NOT created (form validation rejects empty email)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertEqual(
            User.objects.count(),
            initial_count,
            msg=(
                "BUG 1.8 CONFIRMED — User created without email: POST /signup/ with empty "
                "email created a new user account. "
                "isBugCondition_1_8 holds: email is null or empty. "
                "SignUpForm does not require email, so the account is created silently."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.9 — Inactive Product Slug Leaked via Redirect
# isBugCondition_1_9: product EXISTS AND product.is_active == False
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts that /product/<pk>/redirect/ for an inactive product returns 404.
#   On unfixed code, product_detail_by_pk calls get_object_or_404(Product, pk=pk)
#   without filtering on is_active, so it issues a 302 redirect — making the assertion fail.
# ---------------------------------------------------------------------------

class InactiveProductSlugLeakExplorationTest(TestCase):
    """
    **Validates: Requirements 1.9**

    isBugCondition_1_9: product exists AND is_active=False
    Expected (correct) behavior: /product/<pk>/redirect/ returns 404 for inactive products
    Bug behavior (unfixed): returns 302 redirect, revealing the product's slug
    """

    def setUp(self):
        self.category = make_category()
        self.inactive_product = make_product(
            self.category,
            name="Hidden Product",
            slug="hidden-product-slug",
            stock=5,
            is_active=False,
        )

    def test_inactive_product_redirect_returns_404_not_302(self):
        """
        Bug 1.9 exploration: GET /product/<pk>/redirect/ for an inactive product.
        EXPECTED TO FAIL on unfixed code — proves the slug leak bug exists.
        Counterexample: response.status_code == 302 (reveals slug in Location header)
        """
        url = reverse("product_detail_by_pk", kwargs={"pk": self.inactive_product.pk})
        response = self.client.get(url, follow=False)

        # On unfixed code: response.status_code == 302 (bug confirmed — slug leaked)
        # On fixed code: response.status_code == 404
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertEqual(
            response.status_code,
            404,
            msg=(
                f"BUG 1.9 CONFIRMED — Inactive product slug leaked: "
                f"GET /product/{self.inactive_product.pk}/redirect/ returned "
                f"HTTP {response.status_code} (expected 404). "
                f"isBugCondition_1_9 holds: product exists AND is_active=False. "
                f"product_detail_by_pk uses get_object_or_404(Product, pk=pk) without "
                f"is_active=True filter, issuing a 302 to slug={self.inactive_product.slug!r}."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.10 — Broken Password Reset Link
# isBugCondition_1_10: href == '#' or does not resolve
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts the "Forgot Password?" href is NOT '#'.
#   On unfixed code, the login template hardcodes href="#" — making the assertion fail.
# ---------------------------------------------------------------------------

class BrokenPasswordResetExplorationTest(TestCase):
    """
    **Validates: Requirements 1.10**

    isBugCondition_1_10: "Forgot Password?" href == '#' or does not resolve
    Expected (correct) behavior: href resolves to a functional password reset URL
    Bug behavior (unfixed): href is '#' (no-op anchor, no reset flow)
    """

    def test_forgot_password_link_is_not_hash(self):
        """
        Bug 1.10 exploration: parse the login template and assert the "Forgot Password?"
        href is not '#'.
        EXPECTED TO FAIL on unfixed code — proves the broken password reset link bug exists.
        Counterexample: href == '#'
        """
        import re
        from django.conf import settings as django_settings

        # Locate the login template via Django's TEMPLATES DIRS setting
        template_path = None
        for template_dir in django_settings.TEMPLATES[0].get("DIRS", []):
            candidate = os.path.join(template_dir, "login.html")
            if os.path.exists(candidate):
                template_path = candidate
                break

        # Fallback: walk up from this file to find templates/login.html
        if template_path is None:
            base = os.path.dirname(__file__)
            for _ in range(5):
                candidate = os.path.join(base, "templates", "login.html")
                if os.path.exists(candidate):
                    template_path = candidate
                    break
                base = os.path.dirname(base)

        self.assertIsNotNone(template_path, msg="Could not locate templates/login.html")

        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Find the "Forgot Password?" link href
        # The template has the href on the <a> tag line and "Forgot Password?" on the next line.
        # We search for the <a> tag that precedes "Forgot Password?" text.
        import re

        # Match an <a href="..."> tag that is followed (possibly on the next line) by "Forgot Password?"
        forgot_password_href = None
        match = re.search(
            r'<a\s[^>]*href=["\']([^"\']*)["\'][^>]*>\s*Forgot Password\?',
            template_content,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            forgot_password_href = match.group(1)
        else:
            # Fallback: find the <a> tag immediately before "Forgot Password?" text
            match = re.search(
                r'href=["\']([^"\']*)["\'][^>]*>\s*\n\s*Forgot Password\?',
                template_content,
                re.IGNORECASE,
            )
            if match:
                forgot_password_href = match.group(1)

        self.assertIsNotNone(
            forgot_password_href,
            msg="Could not find 'Forgot Password?' link in login template.",
        )

        # On unfixed code: forgot_password_href == '#' (bug confirmed)
        # On fixed code: href resolves to a valid password reset URL
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertNotEqual(
            forgot_password_href,
            "#",
            msg=(
                f"BUG 1.10 CONFIRMED — Broken password reset link: "
                f"'Forgot Password?' href is {forgot_password_href!r} (a no-op anchor). "
                "isBugCondition_1_10 holds: href == '#'. "
                "The login template hardcodes href='#' because no password reset URL "
                "is wired up in core/urls.py and the template was never updated."
            ),
        )

    def test_password_reset_url_is_resolvable(self):
        """
        Bug 1.10 exploration: assert the 'password_reset' URL name resolves.
        EXPECTED TO FAIL on unfixed code — proves no password reset flow is wired up.
        Counterexample: NoReverseMatch raised (URL not registered)
        """
        from django.urls import NoReverseMatch

        try:
            url = reverse("password_reset")
            # If we get here, the URL resolves — but on unfixed code it should not
            # The assertion below will FAIL on unfixed code if the URL does resolve
            # but the href is still '#'. We check both conditions.
            # On fixed code: url is a valid path like '/accounts/password/reset/'
            self.assertNotEqual(
                url,
                "#",
                msg=(
                    "BUG 1.10 CONFIRMED — password_reset URL resolves but login template "
                    "still uses href='#'. Template was not updated to use {% url 'password_reset' %}."
                ),
            )
        except NoReverseMatch:
            # On unfixed code: NoReverseMatch is raised — URL not registered
            # This is the expected bug condition
            self.fail(
                "BUG 1.10 CONFIRMED — Broken password reset: 'password_reset' URL name "
                "does not resolve (NoReverseMatch). "
                "isBugCondition_1_10 holds: href does not resolve to a valid URL pattern. "
                "django.contrib.auth.urls is not included in core/urls.py."
            )


# ---------------------------------------------------------------------------
# Bug 1.11 — Non-functional Newsletter Form
# isBugCondition_1_11: no form element, no action URL, no backend handler
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts the newsletter input IS enclosed in a <form> element.
#   On unfixed code, the footer template has a bare <input> with no surrounding
#   <form> — making the assertion fail.
# ---------------------------------------------------------------------------

class NewsletterFormExplorationTest(TestCase):
    """
    **Validates: Requirements 1.11**

    isBugCondition_1_11: newsletter input has no enclosing <form> element,
                          no action URL, no backend handler
    Expected (correct) behavior: input is wrapped in a <form> with a valid action URL
                                  backed by a handler, OR the input is removed entirely
    Bug behavior (unfixed): bare <input type="email"> with no surrounding <form>
    """

    def _load_base_template(self):
        """Helper: locate and read base.html content."""
        from django.conf import settings as django_settings

        template_path = None
        for template_dir in django_settings.TEMPLATES[0].get("DIRS", []):
            candidate = os.path.join(template_dir, "base.html")
            if os.path.exists(candidate):
                template_path = candidate
                break

        if template_path is None:
            base = os.path.dirname(__file__)
            for _ in range(5):
                candidate = os.path.join(base, "templates", "base.html")
                if os.path.exists(candidate):
                    template_path = candidate
                    break
                base = os.path.dirname(base)

        if template_path is None:
            self.fail("Could not locate templates/base.html")

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_newsletter_input_has_enclosing_form_element(self):
        """
        Bug 1.11 exploration: parse the footer (base.html) template and assert the
        newsletter input is enclosed in a <form> element.
        EXPECTED TO FAIL on unfixed code — proves the non-functional newsletter bug exists.
        Counterexample: newsletter input found outside any <form> element
        """
        template_content = self._load_base_template()

        # Find the newsletter section — look for the email input near "Subscribe"
        # The template has: <input type="email" placeholder="Email address" ...>
        # with no surrounding <form> element
        import re

        # Extract the newsletter section (around the Subscribe button)
        newsletter_section_match = re.search(
            r'(Join the Studio.*?</div>)',
            template_content,
            re.DOTALL | re.IGNORECASE,
        )

        self.assertIsNotNone(
            newsletter_section_match,
            msg="Could not find 'Join the Studio' newsletter section in base.html.",
        )

        newsletter_section = newsletter_section_match.group(1)

        # Check if there is a <form> element enclosing the newsletter input
        has_form_element = bool(re.search(r'<form\b', newsletter_section, re.IGNORECASE))

        # On unfixed code: has_form_element == False (bug confirmed — bare input)
        # On fixed code: has_form_element == True (input wrapped in <form>)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertTrue(
            has_form_element,
            msg=(
                "BUG 1.11 CONFIRMED — Non-functional newsletter form: "
                "the newsletter email input in the footer has no enclosing <form> element. "
                "isBugCondition_1_11 holds: no form element, no action URL, no backend handler. "
                "The input was added as a UI placeholder and never wired up to a backend. "
                "User submissions are silently lost."
            ),
        )

    def test_newsletter_form_has_action_url(self):
        """
        Bug 1.11 exploration: assert the newsletter form has a non-empty action URL.
        EXPECTED TO FAIL on unfixed code — no action URL means submissions go nowhere.
        Counterexample: no <form action="..."> found in newsletter section
        """
        template_content = self._load_base_template()

        import re

        newsletter_section_match = re.search(
            r'(Join the Studio.*?</div>)',
            template_content,
            re.DOTALL | re.IGNORECASE,
        )

        self.assertIsNotNone(
            newsletter_section_match,
            msg="Could not find 'Join the Studio' newsletter section in base.html.",
        )

        newsletter_section = newsletter_section_match.group(1)

        # Check for a form with a non-empty action attribute
        action_match = re.search(
            r'<form\b[^>]*\baction=["\']([^"\']+)["\']',
            newsletter_section,
            re.IGNORECASE,
        )

        # On unfixed code: no form element at all, so no action URL (bug confirmed)
        # On fixed code: form has action pointing to newsletter_subscribe URL
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertIsNotNone(
            action_match,
            msg=(
                "BUG 1.11 CONFIRMED — Newsletter form has no action URL: "
                "no <form action='...'> found in the newsletter section of base.html. "
                "isBugCondition_1_11 holds: no form element, no action URL, no backend handler. "
                "Without an action URL, form submissions cannot reach any backend handler."
            ),
        )
