from decimal import Decimal
from django.conf import settings
from .models import Product
import copy # <--- 1. NEW IMPORT

class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get('session_key')

        if 'session_key' not in request.session:
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

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products from the database.
        """
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        
        # <--- 2. THE FIX: Create a 'Deep Copy' of the cart
        # This creates a safe clone so we don't accidentally write 'Decimals' 
        # back to the real session.
        cart = copy.deepcopy(self.cart) 

        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            # Now we can safely convert to Decimal on the clone
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Calculate the total cost of items in the cart.
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def save(self):
        """
        Mark the session as "modified" to make sure it gets saved.
        """
        self.session.modified = True

    def clear(self):
        """Wipes the cart from the session after a successful purchase."""
        self.session['session_key'] = {}
        self.session.modified = True