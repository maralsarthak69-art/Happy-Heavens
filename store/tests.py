"""
Tests for the Happy Heavens store app.
Covers implementations from Tasks 1-3:
  - Task 1: Security settings
  - Task 2: Data models
  - Task 3: Inventory manager (add_to_cart stock check, checkout stock validation)
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from .cart import Cart
from .exceptions import InsufficientStockError
from .models import Category, Order, OrderItem, Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category(name="Bouquets", slug="bouquets"):
    return Category.objects.create(name=name, slug=slug)


def make_product(category, name="Rose Bouquet", slug="rose-bouquet",
                 price="500.00", stock=10, is_active=True):
    return Product.objects.create(
        category=category,
        name=name,
        slug=slug,
        price=Decimal(price),
        stock=stock,
        is_active=is_active,
    )


def make_user(username="testuser", password="testpass123"):
    return User.objects.create_user(username=username, password=password)


# ---------------------------------------------------------------------------
# Task 2: Data model tests
# ---------------------------------------------------------------------------

class OrderModelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.category = make_category()
        self.product = make_product(self.category)

    def test_order_str(self):
        order = Order.objects.create(
            user=self.user,
            full_name="Jane Doe",
            phone_number="9999999999",
            address="123 Main St",
            city="Pune",
            pincode="411001",
            total_amount=Decimal("500.00"),
        )
        self.assertIn("Jane Doe", str(order))

    def test_order_has_city_and_pincode(self):
        order = Order.objects.create(
            user=self.user,
            full_name="Jane Doe",
            phone_number="9999999999",
            address="123 Main St",
            city="Mumbai",
            pincode="400001",
            total_amount=Decimal("500.00"),
        )
        self.assertEqual(order.city, "Mumbai")
        self.assertEqual(order.pincode, "400001")

    def test_orderitem_str(self):
        order = Order.objects.create(
            user=self.user,
            full_name="Jane Doe",
            phone_number="9999999999",
            address="123 Main St",
            total_amount=Decimal("500.00"),
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=Decimal("500.00"),
        )
        self.assertIn(str(order.id), str(item))

    def test_product_deletion_sets_orderitem_product_null(self):
        """Task 2.3 / Req 2.6: Deleting a product sets OrderItem.product to NULL."""
        order = Order.objects.create(
            user=self.user,
            full_name="Jane Doe",
            phone_number="9999999999",
            address="123 Main St",
            total_amount=Decimal("500.00"),
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=Decimal("500.00"),
        )
        self.product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.product)

    def test_orderitem_price_not_changed_when_product_price_changes(self):
        """Task 2.3 / Req 2.4: OrderItem.price is locked at creation."""
        order = Order.objects.create(
            user=self.user,
            full_name="Jane Doe",
            phone_number="9999999999",
            address="123 Main St",
            total_amount=Decimal("500.00"),
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=Decimal("500.00"),
        )
        # Change the product price
        self.product.price = Decimal("999.00")
        self.product.save()

        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("500.00"))

    def test_product_str(self):
        self.assertEqual(str(self.product), "Rose Bouquet")

    def test_category_str(self):
        self.assertEqual(str(self.category), "Bouquets")


# ---------------------------------------------------------------------------
# Task 3: Inventory manager — add_to_cart stock check
# ---------------------------------------------------------------------------

class AddToCartStockCheckTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.category = make_category()
        self.client.login(username="testuser", password="testpass123")

    def test_add_out_of_stock_product_blocked(self):
        """Req 3.1: Out-of-stock product cannot be added to cart."""
        product = make_product(self.category, stock=0, slug="oos-product")
        response = self.client.get(reverse("add_to_cart", args=[product.pk]))
        # Should redirect back to product detail (slug-based URL), not add to cart
        self.assertRedirects(response, reverse("product_detail", kwargs={"slug": product.slug}))
        # Cart should be empty
        session = self.client.session
        cart_data = session.get("session_key", {})
        self.assertNotIn(str(product.pk), cart_data)

    def test_add_in_stock_product_succeeds(self):
        """Req 3.1: In-stock product can be added to cart."""
        product = make_product(self.category, stock=5, slug="in-stock-product")
        self.client.get(reverse("add_to_cart", args=[product.pk]))
        session = self.client.session
        cart_data = session.get("session_key", {})
        self.assertIn(str(product.pk), cart_data)


# ---------------------------------------------------------------------------
# Task 3: Inventory manager — checkout stock validation
# ---------------------------------------------------------------------------

@override_settings(DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage')
class CheckoutStockValidationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.category = make_category()
        self.client.login(username="testuser", password="testpass123")

    def _add_product_to_cart(self, product, quantity=1):
        """Directly manipulate session to add a product to the cart."""
        session = self.client.session
        cart_data = session.get("session_key", {})
        cart_data[str(product.pk)] = {
            "quantity": quantity,
            "price": str(product.price),
        }
        session["session_key"] = cart_data
        session.save()

    def _checkout_post(self, payment_method="COD"):
        return self.client.post(reverse("checkout"), {
            "full_name": "Jane Doe",
            "phone_number": "9999999999",
            "address": "123 Main St",
            "city": "Pune",
            "pincode": "411001",
            "payment_method": payment_method,
        })

    def test_checkout_rejects_when_stock_insufficient(self):
        """Req 3.2, 3.3: Checkout rejected when cart quantity exceeds stock."""
        product = make_product(self.category, stock=1, slug="low-stock")
        self._add_product_to_cart(product, quantity=5)

        response = self._checkout_post()
        # Should re-render checkout (200), not redirect
        self.assertEqual(response.status_code, 200)
        # No order should have been created
        self.assertEqual(Order.objects.count(), 0)
        # Stock should be unchanged
        product.refresh_from_db()
        self.assertEqual(product.stock, 1)

    def test_checkout_decrements_stock_on_success(self):
        """Req 3.4: Stock is atomically decremented on confirmed order."""
        product = make_product(self.category, stock=10, slug="plenty-stock")
        self._add_product_to_cart(product, quantity=3)

        self._checkout_post()
        product.refresh_from_db()
        self.assertEqual(product.stock, 7)

    def test_checkout_creates_order_on_success(self):
        """Req 3.4: Order is created on successful checkout."""
        product = make_product(self.category, stock=10, slug="order-product")
        self._add_product_to_cart(product, quantity=2)

        self._checkout_post()
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.user, self.user)

    def test_checkout_preserves_cart_on_stock_failure(self):
        """Req 3.3: Cart is preserved when checkout fails due to insufficient stock."""
        product = make_product(self.category, stock=1, slug="preserve-cart")
        self._add_product_to_cart(product, quantity=5)

        self._checkout_post()
        # Cart should still have the item
        session = self.client.session
        cart_data = session.get("session_key", {})
        self.assertIn(str(product.pk), cart_data)

    def test_checkout_requires_login(self):
        """Req 5.5: Unauthenticated users are redirected to login."""
        self.client.logout()
        product = make_product(self.category, stock=5, slug="auth-product")
        self._add_product_to_cart(product, quantity=1)

        response = self.client.get(reverse("checkout"))
        self.assertRedirects(response, "/login/?next=/checkout/")


# ---------------------------------------------------------------------------
# Task 3: InsufficientStockError unit test
# ---------------------------------------------------------------------------

class InsufficientStockErrorTests(TestCase):
    def setUp(self):
        self.category = make_category()

    def test_error_message_contains_product_name(self):
        product = make_product(self.category, name="Lily Bouquet", stock=2)
        error = InsufficientStockError(product)
        self.assertIn("Lily Bouquet", str(error))
        self.assertIn("2", str(error))


# ---------------------------------------------------------------------------
# Task 3: Cart unit tests
# ---------------------------------------------------------------------------

class CartTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category()
        self.product = make_product(self.category, price="250.00", stock=10)

    def _make_request_with_cart(self):
        request = self.factory.get("/")
        request.session = self.client.session
        return request

    def test_cart_add_and_total(self):
        request = self._make_request_with_cart()
        cart = Cart(request)
        cart.add(self.product, quantity=2)
        self.assertEqual(cart.get_total_price(), Decimal("500.00"))

    def test_cart_remove(self):
        request = self._make_request_with_cart()
        cart = Cart(request)
        cart.add(self.product)
        cart.remove(self.product)
        self.assertEqual(len(cart), 0)

    def test_cart_len(self):
        request = self._make_request_with_cart()
        cart = Cart(request)
        cart.add(self.product, quantity=3)
        self.assertEqual(len(cart), 3)


# ---------------------------------------------------------------------------
# Task 16.1: Query optimization — home page assertNumQueries
# ---------------------------------------------------------------------------

class HomePageQueryCountTests(TestCase):
    """Req 12.1, 12.2: Home page renders in ≤ 5 database queries."""

    def setUp(self):
        self.category = make_category()
        # Create a few products with images to exercise prefetch paths
        for i in range(3):
            make_product(
                self.category,
                name=f"Product {i}",
                slug=f"product-{i}",
                stock=10,
            )
        # Warm up the session so session creation queries don't count
        self.client.get(reverse("home"))

    @override_settings(SESSION_SAVE_EVERY_REQUEST=False)
    def test_home_page_query_count(self):
        """Req 12.2: Home page executes ≤ 5 database queries."""
        with self.assertNumQueries(5):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
