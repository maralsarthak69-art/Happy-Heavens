"""
Group C Data Integrity / UX — Preservation Tests
==================================================
These tests run against UNFIXED code and are EXPECTED TO PASS.
They document baseline behavior for non-buggy inputs that must be preserved
after fixes are applied.

Bugs covered:
  1.8  — Valid-email signup continues to create account and store email
  1.9  — Active product /product/<pk>/redirect/ continues to return 302 to slug URL
  1.10 — Other login page elements are unaffected by template change
  1.11 — Other footer elements are unaffected by newsletter form change
  3.7  — Order status change email is still sent when customer has email on file

Validates: Requirements 3.5, 3.7
"""

import os
import re

from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, RequestFactory
from django.urls import reverse

from store.forms import SignUpForm
from store.models import Category, Order, Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category(slug="pres-c-category"):
    return Category.objects.get_or_create(
        slug=slug, defaults={"name": "Pres C Category"}
    )[0]


def make_product(category, name="Pres Product", slug="pres-product-c",
                 stock=5, is_active=True):
    return Product.objects.create(
        category=category,
        name=name,
        slug=slug,
        price="10.00",
        stock=stock,
        is_active=is_active,
    )


def make_user(username="pres_c_user", email="user@example.com", password="StrongPass123!"):
    return User.objects.create_user(username=username, email=email, password=password)


def _load_template(template_name):
    """Locate and read a template file from the templates directory."""
    from django.conf import settings as django_settings

    for template_dir in django_settings.TEMPLATES[0].get("DIRS", []):
        candidate = os.path.join(template_dir, template_name)
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()

    # Fallback: walk up from this file
    base = os.path.dirname(__file__)
    for _ in range(5):
        candidate = os.path.join(base, "templates", template_name)
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()
        base = os.path.dirname(base)

    raise FileNotFoundError(f"Could not locate templates/{template_name}")


# ---------------------------------------------------------------------------
# Bug 1.8 Preservation — Valid-email signup continues to work
# isBugCondition_1_8 returns false: email is non-empty and valid
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class ValidEmailSignupPreservationTest(TestCase):
    """
    **Validates: Requirements 3.7**

    Preservation: SignUpForm with a valid email is accepted, account is created,
    and the email is stored on the user object.
    isBugCondition_1_8 returns false: email is non-empty.
    """

    def test_signup_form_with_valid_email_is_valid(self):
        """
        Preservation 1.8: SignUpForm with a valid email should be valid.
        isBugCondition_1_8 returns false (email is non-empty).
        This must continue to work after the email-required fix is applied.
        """
        form_data = {
            "username": "pres_valid_email",
            "email": "valid@example.com",
            "first_name": "Valid",
            "last_name": "User",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignUpForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            msg=(
                f"Preservation 1.8 FAILED — SignUpForm with valid email should be valid. "
                f"Errors: {form.errors}. "
                "isBugCondition_1_8 returns false (email is non-empty). "
                "Valid-email signup must continue to work after the fix."
            ),
        )

    def test_signup_with_valid_email_creates_user_with_email(self):
        """
        Preservation 1.8: POST /signup/ with valid email creates user and stores email.
        isBugCondition_1_8 returns false (email is non-empty).
        """
        response = self.client.post(
            reverse("signup"),
            data={
                "username": "pres_email_stored",
                "email": "stored@example.com",
                "first_name": "Stored",
                "last_name": "Email",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=False,
        )

        # Should redirect after successful signup
        self.assertIn(
            response.status_code, [301, 302],
            msg=(
                f"Preservation 1.8 FAILED — POST /signup/ with valid email returned "
                f"{response.status_code}, expected a redirect."
            ),
        )

        # User should be created
        self.assertTrue(
            User.objects.filter(username="pres_email_stored").exists(),
            msg="Preservation 1.8 FAILED — user was not created after valid-email signup.",
        )

        # Email should be stored on the user
        user = User.objects.get(username="pres_email_stored")
        self.assertEqual(
            user.email,
            "stored@example.com",
            msg=(
                f"Preservation 1.8 FAILED — user email is {user.email!r}, "
                "expected 'stored@example.com'. Email must be stored after valid signup."
            ),
        )

    def test_signup_form_with_valid_email_saves_email_to_user(self):
        """
        Preservation 1.8: SignUpForm.save() with valid email stores email on User instance.
        """
        form_data = {
            "username": "pres_form_save",
            "email": "form_save@example.com",
            "first_name": "Form",
            "last_name": "Save",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignUpForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form should be valid. Errors: {form.errors}")

        user = form.save()
        self.assertEqual(
            user.email,
            "form_save@example.com",
            msg=(
                f"Preservation 1.8 FAILED — saved user email is {user.email!r}, "
                "expected 'form_save@example.com'."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.9 Preservation — Active product redirect returns 302 to slug URL
# isBugCondition_1_9 returns false: product.is_active == True
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class ActiveProductRedirectPreservationTest(TestCase):
    """
    **Validates: Requirements 3.5**

    Preservation: GET /product/<pk>/redirect/ for an active product returns 302
    to the correct slug URL.
    isBugCondition_1_9 returns false: product.is_active == True.
    """

    def setUp(self):
        self.category = make_category()
        self.active_product = make_product(
            self.category,
            name="Active Redirect Product",
            slug="active-redirect-product",
            stock=5,
            is_active=True,
        )

    def test_active_product_redirect_returns_302(self):
        """
        Preservation 1.9: GET /product/<pk>/redirect/ for an active product returns 302.
        isBugCondition_1_9 returns false (product.is_active == True).
        This must continue to work after the is_active filter fix is applied.
        """
        url = reverse("product_detail_by_pk", kwargs={"pk": self.active_product.pk})
        response = self.client.get(url, follow=False)

        self.assertEqual(
            response.status_code,
            302,
            msg=(
                f"Preservation 1.9 FAILED — GET /product/{self.active_product.pk}/redirect/ "
                f"returned {response.status_code}, expected 302. "
                "isBugCondition_1_9 returns false (product is active). "
                "Active product redirect must continue to work after the fix."
            ),
        )

    def test_active_product_redirect_points_to_slug_url(self):
        """
        Preservation 1.9: The 302 redirect points to the correct slug URL.
        isBugCondition_1_9 returns false (product.is_active == True).
        """
        url = reverse("product_detail_by_pk", kwargs={"pk": self.active_product.pk})
        response = self.client.get(url, follow=False)

        expected_location = reverse(
            "product_detail", kwargs={"slug": self.active_product.slug}
        )
        location = response.get("Location", "")

        self.assertEqual(
            location,
            expected_location,
            msg=(
                f"Preservation 1.9 FAILED — redirect Location is {location!r}, "
                f"expected {expected_location!r}. "
                "Active product redirect must point to the correct slug URL."
            ),
        )

    def test_nonexistent_product_redirect_returns_404(self):
        """
        Preservation 1.9: GET /product/<pk>/redirect/ for a non-existent PK returns 404.
        This edge case must remain correct after the fix.
        """
        url = reverse("product_detail_by_pk", kwargs={"pk": 999999})
        response = self.client.get(url, follow=False)

        self.assertEqual(
            response.status_code,
            404,
            msg=(
                "Preservation 1.9 FAILED — non-existent product PK should return 404, "
                f"but got {response.status_code}."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.10 Preservation — Other login page elements are unaffected
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class LoginPageOtherElementsPreservationTest(TestCase):
    """
    **Validates: Requirements 3.5**

    Preservation: Other login page elements (username field, password field,
    submit button, signup link) are present and unaffected by any template change.
    """

    def _get_login_template(self):
        return _load_template("login.html")

    def test_login_form_username_field_present(self):
        """
        Preservation 1.10: The login template renders the username field via the form.
        The template uses {{ form.username }} (Django template tag) to render the field.
        This must remain present after the password reset link fix.
        """
        content = self._get_login_template()
        # The template uses {{ form.username }} — check for that tag
        has_username = bool(
            re.search(r'\{\{\s*form\.username\s*\}\}', content)
            or re.search(r'name=["\']username["\']', content, re.IGNORECASE)
            or re.search(r'type=["\']text["\']', content, re.IGNORECASE)
        )
        self.assertTrue(
            has_username,
            msg=(
                "Preservation 1.10 FAILED — login template is missing the username field "
                "(expected {{ form.username }} or name='username' or type='text')."
            ),
        )

    def test_login_form_password_field_present(self):
        """
        Preservation 1.10: The login template renders the password field via the form.
        The template uses {{ form.password }} (Django template tag) to render the field.
        This must remain present after the password reset link fix.
        """
        content = self._get_login_template()
        has_password = bool(
            re.search(r'\{\{\s*form\.password\s*\}\}', content)
            or re.search(r'type=["\']password["\']', content, re.IGNORECASE)
            or re.search(r'name=["\']password["\']', content, re.IGNORECASE)
        )
        self.assertTrue(
            has_password,
            msg=(
                "Preservation 1.10 FAILED — login template is missing the password field "
                "(expected {{ form.password }} or type='password' or name='password')."
            ),
        )

    def test_login_form_submit_button_present(self):
        """
        Preservation 1.10: The login template contains a submit button.
        This must remain present after the password reset link fix.
        """
        content = self._get_login_template()
        has_submit = bool(
            re.search(r'type=["\']submit["\']', content, re.IGNORECASE)
            or re.search(r'<button\b', content, re.IGNORECASE)
        )
        self.assertTrue(
            has_submit,
            msg="Preservation 1.10 FAILED — login template is missing a submit button.",
        )

    def test_login_page_renders_successfully(self):
        """
        Preservation 1.10: GET /login/ returns 200 with the login form rendered.
        The page must continue to render correctly after the template fix.
        """
        response = self.client.get(reverse("login"))
        self.assertEqual(
            response.status_code,
            200,
            msg=(
                f"Preservation 1.10 FAILED — GET /login/ returned {response.status_code}, "
                "expected 200."
            ),
        )

    def test_login_page_contains_signup_link(self):
        """
        Preservation 1.10: The login page contains a link to the signup page.
        This must remain present after the password reset link fix.
        """
        content = self._get_login_template()
        has_signup_link = bool(
            re.search(r'signup', content, re.IGNORECASE)
            or re.search(r'register', content, re.IGNORECASE)
            or re.search(r'create.*account', content, re.IGNORECASE)
        )
        self.assertTrue(
            has_signup_link,
            msg="Preservation 1.10 FAILED — login template is missing a signup/register link.",
        )


# ---------------------------------------------------------------------------
# Bug 1.11 Preservation — Other footer elements are unaffected
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class FooterOtherElementsPreservationTest(TestCase):
    """
    **Validates: Requirements 3.5**

    Preservation: Other footer elements (navigation links, brand name, social links)
    are present and unaffected by any newsletter form change.
    """

    def _get_base_template(self):
        return _load_template("base.html")

    def test_footer_contains_brand_or_store_name(self):
        """
        Preservation 1.11: The footer contains the store brand name.
        This must remain present after the newsletter form fix.
        """
        content = self._get_base_template()
        # Look for "Happy Heavens" or similar brand reference in the footer area
        footer_match = re.search(
            r'<footer\b.*?</footer>',
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if footer_match:
            footer_content = footer_match.group(0)
        else:
            # Fallback: search the whole template
            footer_content = content

        has_brand = bool(
            re.search(r'happy\s*heavens', footer_content, re.IGNORECASE)
            or re.search(r'studio', footer_content, re.IGNORECASE)
        )
        self.assertTrue(
            has_brand,
            msg=(
                "Preservation 1.11 FAILED — footer does not contain the store brand name. "
                "Footer brand must remain after the newsletter form fix."
            ),
        )

    def test_base_template_renders_successfully(self):
        """
        Preservation 1.11: The home page (which uses base.html) renders with 200.
        The base template must continue to render correctly after the newsletter fix.
        """
        response = self.client.get(reverse("home"))
        self.assertEqual(
            response.status_code,
            200,
            msg=(
                f"Preservation 1.11 FAILED — GET / returned {response.status_code}, "
                "expected 200. base.html must render correctly after the newsletter fix."
            ),
        )

    def test_footer_contains_navigation_links(self):
        """
        Preservation 1.11: The footer contains navigation links (shop, customize, etc.).
        These must remain present after the newsletter form fix.
        """
        content = self._get_base_template()
        # Look for common navigation links in the footer
        has_nav = bool(
            re.search(r'href=["\']/', content, re.IGNORECASE)
        )
        self.assertTrue(
            has_nav,
            msg=(
                "Preservation 1.11 FAILED — base template has no navigation links. "
                "Footer navigation must remain after the newsletter form fix."
            ),
        )


# ---------------------------------------------------------------------------
# Order Email Preservation (3.7) — Email sent when customer has email on file
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class OrderStatusEmailPreservationTest(TestCase):
    """
    **Validates: Requirements 3.7**

    Preservation: When an order's status changes and the customer has an email
    address on file, the post_save signal sends a status-change email.
    This must continue to work after the email-required fix is applied.
    """

    def setUp(self):
        self.category = make_category(slug="order-email-pres-cat")
        self.user_with_email = make_user(
            username="order_email_user",
            email="customer@example.com",
            password="StrongPass123!",
        )

    def _create_order(self, user, status="PENDING"):
        return Order.objects.create(
            user=user,
            full_name="Test Customer",
            phone_number="1234567890",
            address="123 Test Street",
            city="Test City",
            pincode="12345",
            total_amount="100.00",
            payment_method="COD",
            status=status,
        )

    def test_order_status_change_sends_email_when_user_has_email(self):
        """
        Preservation 3.7: Changing an order's status sends an email to the customer
        when the user has an email address on file.
        isBugCondition_1_8 returns false (user has email).
        This must continue to work after the email-required fix is applied.
        """
        order = self._create_order(self.user_with_email, status="PENDING")

        # Change the order status — this should trigger the post_save signal
        order.status = "CONFIRMED"
        order.save()

        # One email should have been sent
        self.assertEqual(
            len(mail.outbox),
            1,
            msg=(
                f"Preservation 3.7 FAILED — expected 1 email sent after order status change, "
                f"got {len(mail.outbox)}. "
                "Order status change email must be sent when customer has email on file."
            ),
        )

    def test_order_status_change_email_has_correct_recipient(self):
        """
        Preservation 3.7: The status-change email is sent to the customer's email address.
        """
        order = self._create_order(self.user_with_email, status="PENDING")
        order.status = "SHIPPED"
        order.save()

        self.assertEqual(len(mail.outbox), 1,
                         msg="Precondition: one email should be sent.")
        self.assertIn(
            "customer@example.com",
            mail.outbox[0].to,
            msg=(
                "Preservation 3.7 FAILED — email was not sent to the customer's address. "
                f"Recipients: {mail.outbox[0].to}"
            ),
        )

    def test_order_status_change_email_contains_order_id(self):
        """
        Preservation 3.7: The status-change email subject or body references the order ID.
        """
        order = self._create_order(self.user_with_email, status="PENDING")
        order.status = "DELIVERED"
        order.save()

        self.assertEqual(len(mail.outbox), 1,
                         msg="Precondition: one email should be sent.")
        email = mail.outbox[0]
        order_id_str = str(order.id)
        has_order_id = (
            order_id_str in email.subject
            or order_id_str in email.body
        )
        self.assertTrue(
            has_order_id,
            msg=(
                f"Preservation 3.7 FAILED — order ID {order.id} not found in email "
                f"subject ({email.subject!r}) or body. "
                "Email should reference the order ID."
            ),
        )

    def test_order_creation_does_not_send_email(self):
        """
        Preservation 3.7: Creating a new order does NOT send an email (only status
        changes trigger the notification). This baseline must be preserved.
        """
        self._create_order(self.user_with_email, status="PENDING")

        self.assertEqual(
            len(mail.outbox),
            0,
            msg=(
                f"Preservation 3.7 FAILED — order creation should not send an email, "
                f"but {len(mail.outbox)} email(s) were sent."
            ),
        )

    def test_order_status_unchanged_does_not_send_email(self):
        """
        Preservation 3.7: Saving an order without changing its status does NOT send
        an email. Only actual status changes trigger the notification.
        """
        order = self._create_order(self.user_with_email, status="PENDING")
        # Save without changing status
        order.save()

        self.assertEqual(
            len(mail.outbox),
            0,
            msg=(
                f"Preservation 3.7 FAILED — saving order without status change should not "
                f"send an email, but {len(mail.outbox)} email(s) were sent."
            ),
        )

    def test_no_email_sent_when_user_has_no_email(self):
        """
        Preservation 3.7: When the user has no email address, no email is sent.
        This is the existing guard in the signal (if customer_email:) and must be preserved.
        """
        user_no_email = User.objects.create_user(
            username="no_email_user",
            email="",
            password="StrongPass123!",
        )
        order = self._create_order(user_no_email, status="PENDING")
        order.status = "CONFIRMED"
        order.save()

        self.assertEqual(
            len(mail.outbox),
            0,
            msg=(
                "Preservation 3.7 FAILED — no email should be sent when user has no email, "
                f"but {len(mail.outbox)} email(s) were sent."
            ),
        )
