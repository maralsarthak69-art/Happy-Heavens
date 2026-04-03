"""
Group B Cart Logic — Bug Condition Exploration Tests
=====================================================
These tests run against UNFIXED code and are EXPECTED TO FAIL.
Failure confirms the bugs exist. DO NOT fix the code or tests when they fail.

Bugs covered:
  1.5 — Cart Quantity Exceeds Stock (stock overflow)
  1.6 — Cart.__len__ Counts Inactive Products (inflated badge count)
  1.7 — Cart Mutation via GET Request (CSRF-unsafe cart mutation)

Validates: Requirements 1.5, 1.6, 1.7
"""

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.urls import reverse

from store.cart import Cart
from store.models import Category, Product

# RequestFactory is used by the InactiveCountExplorationTest (Bug 1.6)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category():
    return Category.objects.create(name="Test Category", slug="test-category")


def make_product(category, name="Test Product", slug="test-product", stock=5, is_active=True):
    return Product.objects.create(
        category=category,
        name=name,
        slug=slug,
        price="10.00",
        stock=stock,
        is_active=is_active,
    )


def make_user(username="carttest", password="cartpass123"):
    return User.objects.create_user(username=username, password=password)


# ---------------------------------------------------------------------------
# Bug 1.5 — Cart Quantity Exceeds Stock (Stock Overflow)
# isBugCondition_1_5: current_cart_quantity + 1 > product.stock
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts that after adding a stock=1 product twice, the cart
#   quantity does NOT exceed stock (i.e. quantity <= 1).
#   On unfixed code, Cart.add increments unconditionally, so quantity becomes 2
#   (exceeding stock=1) — making the assertion fail.
# ---------------------------------------------------------------------------

class StockOverflowExplorationTest(TestCase):
    """
    **Validates: Requirements 1.5**

    isBugCondition_1_5: current_cart_quantity + 1 > product.stock
    Scoped case: stock=1, add twice → quantity=2 (exceeds stock)

    Expected (correct) behavior: second add is rejected; quantity stays at 1
    Bug behavior (unfixed): quantity becomes 2, exceeding available stock
    """

    def setUp(self):
        self.category = make_category()
        self.product = make_product(
            self.category, name="Limited Item", slug="limited-item", stock=1
        )

    def test_adding_product_twice_does_not_exceed_stock(self):
        """
        Bug 1.5 exploration: add a product with stock=1 to the cart twice via the view.
        EXPECTED TO FAIL on unfixed code — proves the stock overflow bug exists.
        Counterexample: cart[product_id]['quantity'] == 2 (exceeds stock=1)
        """
        url = reverse("add_to_cart", kwargs={"pk": self.product.pk})

        # First add — should succeed (qty 0 → 1, within stock=1)
        self.client.get(url, follow=False)

        # Second add — should be rejected on fixed code (qty 1 + 1 > stock=1)
        # On unfixed code: Cart.add increments unconditionally → qty becomes 2
        self.client.get(url, follow=False)

        session_cart = self.client.session.get("session_key", {})
        product_id = str(self.product.id)
        actual_quantity = session_cart.get(product_id, {}).get("quantity", 0)

        # On unfixed code: actual_quantity == 2 (bug confirmed)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertLessEqual(
            actual_quantity,
            self.product.stock,
            msg=(
                f"BUG 1.5 CONFIRMED — Stock overflow: cart quantity is {actual_quantity} "
                f"but product.stock is {self.product.stock}. "
                "isBugCondition_1_5 holds: current_qty + 1 > product.stock. "
                "Cart.add increments unconditionally without checking stock cap."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.6 — Cart.__len__ Counts Inactive Products
# isBugCondition_1_6: inactive product IDs present in session cart
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts len(cart) equals only the active product quantity (2),
#   not the total including the inactive product (3).
#   On unfixed code, Cart.__len__ sums all session values unconditionally,
#   returning 3 — making the assertion fail.
# ---------------------------------------------------------------------------

class InactiveCountExplorationTest(TestCase):
    """
    **Validates: Requirements 1.6**

    isBugCondition_1_6: inactive product IDs present in session cart
    Scoped case: one active product (qty=2) + one inactive product (qty=1) in session

    Expected (correct) behavior: len(cart) == 2 (only active product counted)
    Bug behavior (unfixed): len(cart) == 3 (inactive product included in count)
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category()
        self.active_product = make_product(
            self.category, name="Active Product", slug="active-product", stock=5, is_active=True
        )
        self.inactive_product = make_product(
            self.category, name="Inactive Product", slug="inactive-product", stock=3, is_active=False
        )

    def test_len_excludes_inactive_products(self):
        """
        Bug 1.6 exploration: cart session with active product (qty=2) and inactive product (qty=1).
        EXPECTED TO FAIL on unfixed code — proves the inactive count bug exists.
        Counterexample: len(cart) == 3 (inactive product included)
        """
        request = self.factory.get("/")
        # Manually build the session cart to simulate the bug condition:
        # both active and inactive product IDs are present in the session
        request.session = {
            "session_key": {
                str(self.active_product.id): {"quantity": 2, "price": "10.00"},
                str(self.inactive_product.id): {"quantity": 1, "price": "10.00"},
            }
        }

        cart = Cart(request)

        actual_len = len(cart)

        # On unfixed code: len(cart) == 3 (bug confirmed — inactive product counted)
        # On fixed code: len(cart) == 2 (only active product counted)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertEqual(
            actual_len,
            2,
            msg=(
                f"BUG 1.6 CONFIRMED — Inactive count: len(cart) is {actual_len} "
                "but should be 2 (only active product qty=2). "
                "isBugCondition_1_6 holds: inactive product ID present in session. "
                "Cart.__len__ sums all session values without filtering inactive products."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.7 — Cart Mutation via GET Request
# isBugCondition_1_7: request.method == 'GET'
#
# EXPECTED TO FAIL on unfixed code:
#   The test asserts that a GET request to /cart/add/<pk>/ does NOT add the
#   product to the cart (i.e. the cart remains empty).
#   On unfixed code, add_to_cart has no @require_POST guard, so the GET
#   request mutates the cart — making the assertion fail.
# ---------------------------------------------------------------------------

class GetCartMutationExplorationTest(TestCase):
    """
    **Validates: Requirements 1.7**

    isBugCondition_1_7: request.method == 'GET' to /cart/add/<pk>/
    Expected (correct) behavior: GET returns 405, cart is unchanged
    Bug behavior (unfixed): GET adds the product to the cart
    """

    def setUp(self):
        self.category = make_category()
        self.product = make_product(
            self.category, name="Cart Item", slug="cart-item", stock=5
        )

    def test_get_request_does_not_add_product_to_cart(self):
        """
        Bug 1.7 exploration: GET /cart/add/<pk>/ should NOT mutate the cart.
        EXPECTED TO FAIL on unfixed code — proves the GET cart mutation bug exists.
        Counterexample: product is present in session cart after GET request
        """
        # Start with an empty cart (no session data)
        response = self.client.get(
            reverse("add_to_cart", kwargs={"pk": self.product.pk}),
            follow=False,
        )

        # Check the session cart after the GET request
        session_cart = self.client.session.get("session_key", {})
        product_id = str(self.product.id)
        product_in_cart = product_id in session_cart

        # On unfixed code: product IS in cart after GET (bug confirmed)
        # The assertion below will FAIL on unfixed code, confirming the bug.
        self.assertFalse(
            product_in_cart,
            msg=(
                f"BUG 1.7 CONFIRMED — GET cart mutation: GET /cart/add/{self.product.pk}/ "
                f"added product {product_id!r} to the cart without a POST request. "
                "isBugCondition_1_7 holds: request.method == 'GET'. "
                "add_to_cart view has no @require_POST guard."
            ),
        )
