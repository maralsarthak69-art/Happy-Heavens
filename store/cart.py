from decimal import Decimal
from django.conf import settings
from .models import Product
import copy # <--- 1. NEW IMPORT

class Cart:
    def __init__(self, request):
        """
        Initialize the cart. Creates a new empty cart if none exists in the session.
        Handles corrupted session data gracefully.
        """
        self.session = request.session
        cart = self.session.get('session_key')

        if not isinstance(cart, dict):
            # Covers both missing key and corrupted/non-dict session data
            cart = self.session['session_key'] = {}

        self.cart = cart

    def add(self, product, quantity=1):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        
        self.cart[product_id]['quantity'] += quantity
        self.save()

    def remove(self, product):
        """
        Remove a product from the cart.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def update(self, product, quantity):
        """
        Set the quantity of a cart item directly.
        Removes the item if quantity <= 0.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            if quantity <= 0:
                self.remove(product)
            else:
                self.cart[product_id]['quantity'] = quantity
                self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products from the database.
        Filters out products where is_active=False and flags them in self.removed_items.
        """
        self.removed_items = []
        product_ids = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids)

        # Build a map of active products; collect inactive ones for removal
        active_products = {}
        for product in products:
            if not product.is_active:
                self.removed_items.append(product)
                product_id = str(product.id)
                if product_id in self.cart:
                    del self.cart[product_id]
                    self.session.modified = True
            else:
                active_products[str(product.id)] = product

        # Deep copy to avoid writing Decimals back to the session
        cart = copy.deepcopy(self.cart)

        for product_id, product in active_products.items():
            if product_id in cart:
                cart[product_id]['product'] = product

        for item in cart.values():
            # Only yield items that have a product attached (i.e. active ones)
            if 'product' not in item:
                continue
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Count only active items in the cart.
        Excludes quantities for products that have been deactivated.
        """
        active_ids = set(
            str(pk) for pk in Product.objects.filter(
                id__in=self.cart.keys(), is_active=True
            ).values_list('id', flat=True)
        )
        return sum(
            item['quantity']
            for pid, item in self.cart.items()
            if pid in active_ids
        )

    def get_total_price(self):
        """
        Calculate the total cost of active items in the cart.
        Queries only active products to avoid including deactivated items in the total.
        """
        product_ids = list(self.cart.keys())
        active_ids = set(
            str(pk) for pk in Product.objects.filter(
                id__in=product_ids, is_active=True
            ).values_list('id', flat=True)
        )
        return sum(
            Decimal(item['price']) * item['quantity']
            for pid, item in self.cart.items()
            if pid in active_ids
        )

    def save(self):
        """
        Mark the session as "modified" to make sure it gets saved.
        """
        self.session.modified = True

    def clear(self):
        """Wipes the cart from the session after a successful purchase."""
        self.session['session_key'] = {}
        self.session.modified = True