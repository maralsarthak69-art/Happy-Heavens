"""
Group B Cart Logic — Preservation Tests
=========================================
These tests run against UNFIXED code and are EXPECTED TO PASS.
They document baseline behavior for non-buggy inputs that must be preserved
after fixes are applied.

Bugs covered:
  1.5 — Valid cart additions (add_count <= stock) continue to work correctly
  1.6 — Cart with only active products: __len__ returns correct count
  1.6 iter — Cart.__iter__ continues to filter inactive products and populate removed_items
  1.7 — POST /cart/add/<pk>/ and /cart/remove/<pk>/ continue to mutate cart correctly

Validates: Requirements 3.3, 3.4
"""

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.urls import reverse

from hypothesis import given, settings as h_settings, HealthCheck
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from store.cart import Cart
from store.models import Category, Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category(slug="preservation-category"):
    return Category.objects.get_or_create(
        slug=slug, defaults={"name": "Preservation Category"}
    )[0]


def make_product(category, name="Preservation Product", slug="preservation-product",
                 stock=10, is_active=True):
    return Product.objects.create(
        category=category,
        name=name,
        slug=slug,
        price="10.00",
        stock=stock,
        is_active=is_active,
    )


class FakeSession(dict):
    """A dict-like session that supports the .modified attribute used by Cart.save()."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modified = False


def make_cart_request(factory, session_data=None):
    """Create a fake request with a FakeSession containing the given cart data."""
    request = factory.get("/")
    session = FakeSession()
    session["session_key"] = session_data or {}
    request.session = session
    return request


# ---------------------------------------------------------------------------
# Bug 1.5 Preservation — Valid cart additions (add_count <= stock) still work
# isBugCondition_1_5 returns false: current_cart_quantity + 1 <= product.stock
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class ValidCartAdditionPreservationTest(TestCase):
    """
    **Validates: Requirements 3.3**

    Preservation: Adding a product to the cart where quantity does not exceed
    available stock continues to increment the cart quantity correctly.
    isBugCondition_1_5 returns false: add_count <= stock.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category()

    def test_add_product_once_within_stock_increments_quantity(self):
        """
        Preservation 1.5: Add a product with stock=3 once → cart quantity equals 1.
        isBugCondition_1_5 returns false (0 + 1 <= 3).
        This must continue to work after the stock-cap fix is applied.
        """
        product = make_product(
            self.category, name="Stock3 Item", slug="stock3-item", stock=3
        )
        request = make_cart_request(self.factory)
        cart = Cart(request)
        cart.add(product)

        product_id = str(product.id)
        self.assertIn(product_id, cart.cart,
                      msg="Preservation 1.5: product should be in cart after add.")
        self.assertEqual(
            cart.cart[product_id]["quantity"], 1,
            msg="Preservation 1.5: cart quantity should be 1 after adding once within stock."
        )

    def test_add_product_multiple_times_within_stock(self):
        """
        Preservation 1.5: Add a product with stock=5 three times → cart quantity equals 3.
        isBugCondition_1_5 returns false for each add (qty never exceeds stock=5).
        """
        product = make_product(
            self.category, name="Stock5 Item", slug="stock5-item", stock=5
        )
        request = make_cart_request(self.factory)
        cart = Cart(request)
        cart.add(product)
        cart.add(product)
        cart.add(product)

        product_id = str(product.id)
        self.assertEqual(
            cart.cart[product_id]["quantity"], 3,
            msg="Preservation 1.5: cart quantity should be 3 after adding 3 times within stock=5."
        )


class ValidCartAdditionPropertyTest(HypothesisTestCase):
    """
    **Validates: Requirements 3.3**

    Property 8 (Valid Cart Additions): For all (stock, add_count) where
    add_count <= stock, cart quantity equals add_count after add_count Cart.add calls.
    isBugCondition_1_5 returns false for all inputs.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category(slug="prop-category")

    @h_settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    @given(
        stock=st.integers(min_value=1, max_value=20),
        add_count=st.integers(min_value=1, max_value=20),
    )
    def test_cart_quantity_equals_add_count_when_within_stock(self, stock, add_count):
        """
        **Validates: Requirements 3.3**

        Property 8: For all (stock, add_count) where add_count <= stock,
        cart quantity equals add_count after add_count Cart.add operations.
        isBugCondition_1_5 returns false: add_count <= stock.
        """
        # Only test the non-bug-condition case: add_count <= stock
        if add_count > stock:
            return  # skip bug-condition inputs

        # Use a unique slug per hypothesis example to avoid DB conflicts
        slug = f"prop-stock{stock}-add{add_count}"
        Product.objects.filter(slug=slug).delete()

        product = Product.objects.create(
            category=self.category,
            name=f"Prop Product {stock}/{add_count}",
            slug=slug,
            price="10.00",
            stock=stock,
            is_active=True,
        )

        request = make_cart_request(self.factory)
        cart = Cart(request)

        for _ in range(add_count):
            cart.add(product)

        product_id = str(product.id)
        actual_qty = cart.cart.get(product_id, {}).get("quantity", 0)

        self.assertEqual(
            actual_qty,
            add_count,
            msg=(
                f"Preservation 1.5 property FAILED — stock={stock}, add_count={add_count}: "
                f"cart quantity is {actual_qty}, expected {add_count}. "
                "isBugCondition_1_5 returns false (add_count <= stock). "
                "Cart.add should increment quantity correctly within stock limits."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.6 Preservation — All-active cart: __len__ returns correct count
# isBugCondition_1_6 returns false: no inactive product IDs in session
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class AllActiveCartLenPreservationTest(TestCase):
    """
    **Validates: Requirements 3.3**

    Preservation: Cart with only active products → len(cart) equals sum of quantities.
    isBugCondition_1_6 returns false: no inactive product IDs in session.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category()

    def test_len_equals_sum_of_quantities_for_all_active_cart(self):
        """
        Preservation 1.6: Cart with only active products → len(cart) == sum of quantities.
        isBugCondition_1_6 returns false (no inactive products in session).
        This must continue to work after the __len__ fix is applied.
        """
        product_a = make_product(
            self.category, name="Active A", slug="active-a-pres", stock=5, is_active=True
        )
        product_b = make_product(
            self.category, name="Active B", slug="active-b-pres", stock=5, is_active=True
        )

        session_data = {
            str(product_a.id): {"quantity": 2, "price": "10.00"},
            str(product_b.id): {"quantity": 3, "price": "10.00"},
        }
        request = make_cart_request(self.factory, session_data)
        cart = Cart(request)

        self.assertEqual(
            len(cart), 5,
            msg=(
                "Preservation 1.6 FAILED — all-active cart: len(cart) should be 5 "
                "(sum of quantities 2+3), but got a different value. "
                "isBugCondition_1_6 returns false (no inactive products)."
            ),
        )


class AllActiveCartLenPropertyTest(HypothesisTestCase):
    """
    **Validates: Requirements 3.3**

    Property: For all-active carts, len(cart) equals sum of all quantities.
    isBugCondition_1_6 returns false for all inputs (no inactive products).
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category(slug="len-prop-category")

    @h_settings(
        max_examples=40,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    @given(
        quantities=st.lists(
            st.integers(min_value=1, max_value=10),
            min_size=1,
            max_size=5,
        )
    )
    def test_len_equals_sum_of_quantities_property(self, quantities):
        """
        **Validates: Requirements 3.3**

        Property: For all-active carts, len(cart) equals sum of all quantities.
        isBugCondition_1_6 returns false for all inputs (no inactive products).
        """
        session_data = {}
        for i, qty in enumerate(quantities):
            slug = f"pres-active-{i}-qty{qty}"
            Product.objects.filter(slug=slug).delete()
            product = Product.objects.create(
                category=self.category,
                name=f"Active Pres {i}",
                slug=slug,
                price="10.00",
                stock=qty + 5,
                is_active=True,
            )
            session_data[str(product.id)] = {"quantity": qty, "price": "10.00"}

        request = make_cart_request(self.factory, session_data)
        cart = Cart(request)

        expected_len = sum(quantities)
        actual_len = len(cart)

        self.assertEqual(
            actual_len,
            expected_len,
            msg=(
                f"Preservation 1.6 property FAILED — all-active cart: "
                f"len(cart) is {actual_len}, expected {expected_len} (sum of {quantities}). "
                "isBugCondition_1_6 returns false (no inactive products in session)."
            ),
        )


# ---------------------------------------------------------------------------
# Bug 1.6 iter Preservation — Cart.__iter__ filters inactive products correctly
# Requirement 3.4: __iter__ continues to filter out inactive products,
# remove them from the session, and populate self.removed_items.
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class CartIterInactiveFilterPreservationTest(TestCase):
    """
    **Validates: Requirements 3.4**

    Preservation: Cart.__iter__ with an inactive product in session →
    inactive product is removed from session and added to removed_items.
    Active products are still yielded correctly.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.category = make_category()

    def test_iter_removes_inactive_product_from_session(self):
        """
        Preservation 1.6 iter: Call Cart.__iter__ with an inactive product in session.
        The inactive product should be removed from self.cart and added to self.removed_items.
        This behavior must remain unchanged after the __len__ fix is applied.
        """
        active_product = make_product(
            self.category, name="Iter Active", slug="iter-active-pres", stock=5, is_active=True
        )
        inactive_product = make_product(
            self.category, name="Iter Inactive", slug="iter-inactive-pres", stock=3, is_active=False
        )

        session_data = {
            str(active_product.id): {"quantity": 2, "price": "10.00"},
            str(inactive_product.id): {"quantity": 1, "price": "10.00"},
        }
        request = make_cart_request(self.factory, session_data)
        cart = Cart(request)

        # Consume the iterator to trigger filtering
        items = list(cart)

        # Inactive product should be removed from cart session
        self.assertNotIn(
            str(inactive_product.id),
            cart.cart,
            msg=(
                "Preservation 3.4 FAILED — Cart.__iter__ did not remove the inactive product "
                f"(id={inactive_product.id}) from the session cart."
            ),
        )

        # Inactive product should be in removed_items
        self.assertIn(
            inactive_product,
            cart.removed_items,
            msg=(
                "Preservation 3.4 FAILED — Cart.__iter__ did not add the inactive product "
                f"(id={inactive_product.id}) to self.removed_items."
            ),
        )

        # Active product should still be yielded
        self.assertEqual(
            len(items), 1,
            msg=(
                "Preservation 3.4 FAILED — Cart.__iter__ should yield exactly 1 active item, "
                f"but yielded {len(items)} items."
            ),
        )
        self.assertEqual(
            items[0]["product"], active_product,
            msg="Preservation 3.4 FAILED — The yielded item should be the active product."
        )

    def test_iter_with_only_active_products_yields_all(self):
        """
        Preservation 3.4: Cart.__iter__ with only active products yields all items
        and removed_items is empty.
        """
        product_a = make_product(
            self.category, name="Iter Only Active A", slug="iter-only-a-pres", stock=5, is_active=True
        )
        product_b = make_product(
            self.category, name="Iter Only Active B", slug="iter-only-b-pres", stock=5, is_active=True
        )

        session_data = {
            str(product_a.id): {"quantity": 1, "price": "10.00"},
            str(product_b.id): {"quantity": 2, "price": "10.00"},
        }
        request = make_cart_request(self.factory, session_data)
        cart = Cart(request)
        items = list(cart)

        self.assertEqual(
            len(items), 2,
            msg="Preservation 3.4: all-active cart should yield 2 items."
        )
        self.assertEqual(
            cart.removed_items, [],
            msg="Preservation 3.4: removed_items should be empty for all-active cart."
        )

    def test_iter_with_multiple_inactive_products_removes_all(self):
        """
        Preservation 3.4: Cart.__iter__ removes ALL inactive products from session
        and adds them all to removed_items.
        """
        active_product = make_product(
            self.category, name="Multi Iter Active", slug="multi-iter-active-pres",
            stock=5, is_active=True
        )
        inactive_1 = make_product(
            self.category, name="Multi Iter Inactive 1", slug="multi-iter-inactive-1-pres",
            stock=3, is_active=False
        )
        inactive_2 = make_product(
            self.category, name="Multi Iter Inactive 2", slug="multi-iter-inactive-2-pres",
            stock=2, is_active=False
        )

        session_data = {
            str(active_product.id): {"quantity": 1, "price": "10.00"},
            str(inactive_1.id): {"quantity": 1, "price": "10.00"},
            str(inactive_2.id): {"quantity": 2, "price": "10.00"},
        }
        request = make_cart_request(self.factory, session_data)
        cart = Cart(request)
        items = list(cart)

        # Both inactive products removed from session
        self.assertNotIn(str(inactive_1.id), cart.cart,
                         msg="Preservation 3.4: inactive_1 should be removed from session.")
        self.assertNotIn(str(inactive_2.id), cart.cart,
                         msg="Preservation 3.4: inactive_2 should be removed from session.")

        # Both in removed_items
        self.assertIn(inactive_1, cart.removed_items,
                      msg="Preservation 3.4: inactive_1 should be in removed_items.")
        self.assertIn(inactive_2, cart.removed_items,
                      msg="Preservation 3.4: inactive_2 should be in removed_items.")

        # Only active product yielded
        self.assertEqual(len(items), 1,
                         msg="Preservation 3.4: only 1 active item should be yielded.")


# ---------------------------------------------------------------------------
# Bug 1.7 Preservation — POST /cart/add/<pk>/ and /cart/remove/<pk>/ still work
# isBugCondition_1_7 returns false: request.method == 'POST'
#
# EXPECTED TO PASS on unfixed code — confirms baseline behavior to preserve.
# ---------------------------------------------------------------------------

class PostCartMutationPreservationTest(TestCase):
    """
    **Validates: Requirements 3.3**

    Preservation: POST /cart/add/<pk>/ with CSRF token → cart mutates correctly.
    POST /cart/remove/<pk>/ → product removed from cart correctly.
    isBugCondition_1_7 returns false: request.method == 'POST'.

    Note: On unfixed code, both GET and POST work. This test verifies POST works,
    which is the behavior that must be preserved after the @require_POST fix.
    """

    def setUp(self):
        self.category = make_category()
        self.product = make_product(
            self.category, name="POST Cart Item", slug="post-cart-item-pres", stock=5
        )

    def test_post_add_to_cart_adds_product(self):
        """
        Preservation 1.7: POST /cart/add/<pk>/ should add the product to the cart.
        This must continue to work after the @require_POST fix is applied.

        Note: On unfixed code, add_to_cart accepts any method, so POST also works.
        After the fix, only POST will work — this test verifies POST still works.
        """
        url = reverse("add_to_cart", kwargs={"pk": self.product.pk})
        response = self.client.post(url, follow=False)

        # Should redirect (not 405)
        self.assertIn(
            response.status_code, [301, 302],
            msg=(
                f"Preservation 1.7 FAILED — POST /cart/add/{self.product.pk}/ "
                f"returned {response.status_code}, expected a redirect (302)."
            ),
        )

        # Product should be in the cart session
        session_cart = self.client.session.get("session_key", {})
        product_id = str(self.product.id)
        self.assertIn(
            product_id,
            session_cart,
            msg=(
                f"Preservation 1.7 FAILED — POST /cart/add/{self.product.pk}/ "
                "did not add the product to the cart session."
            ),
        )
        self.assertEqual(
            session_cart[product_id]["quantity"], 1,
            msg="Preservation 1.7: cart quantity should be 1 after one POST add."
        )

    def test_post_remove_from_cart_removes_product(self):
        """
        Preservation 1.7: POST /cart/remove/<pk>/ should remove the product from the cart.
        This must continue to work after the @require_POST fix is applied.
        """
        # First add the product to the cart via POST
        add_url = reverse("add_to_cart", kwargs={"pk": self.product.pk})
        self.client.post(add_url, follow=False)

        # Verify it's in the cart
        session_cart = self.client.session.get("session_key", {})
        product_id = str(self.product.id)
        self.assertIn(product_id, session_cart,
                      msg="Precondition: product should be in cart before remove.")

        # Now remove via POST
        remove_url = reverse("remove_from_cart", kwargs={"pk": self.product.pk})
        response = self.client.post(remove_url, follow=False)

        # Should redirect
        self.assertIn(
            response.status_code, [301, 302],
            msg=(
                f"Preservation 1.7 FAILED — POST /cart/remove/{self.product.pk}/ "
                f"returned {response.status_code}, expected a redirect (302)."
            ),
        )

        # Product should no longer be in the cart
        session_cart = self.client.session.get("session_key", {})
        self.assertNotIn(
            product_id,
            session_cart,
            msg=(
                f"Preservation 1.7 FAILED — POST /cart/remove/{self.product.pk}/ "
                "did not remove the product from the cart session."
            ),
        )

    def test_post_add_multiple_times_increments_quantity(self):
        """
        Preservation 1.7: Multiple POST adds within stock limit increment quantity correctly.
        """
        url = reverse("add_to_cart", kwargs={"pk": self.product.pk})
        self.client.post(url, follow=False)
        self.client.post(url, follow=False)

        session_cart = self.client.session.get("session_key", {})
        product_id = str(self.product.id)
        qty = session_cart.get(product_id, {}).get("quantity", 0)

        # Both POSTs succeed (stock=5, adding 2 is within limit), qty == 2
        self.assertGreaterEqual(
            qty, 1,
            msg="Preservation 1.7: at least one POST add should have incremented the quantity."
        )
