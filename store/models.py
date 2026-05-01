from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Category Name",
        help_text="e.g. Bouquets, Hampers, Candles",
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="URL Name",
        help_text="This is filled automatically — you don't need to change it.",
    )

    class Meta:
        verbose_name        = "Category"
        verbose_name_plural = "Categories"
        ordering            = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name="Category",
        help_text="Which category does this product belong to?",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Product Name",
        help_text="The name customers will see on the website.",
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="URL Name",
        help_text="Filled automatically from the product name — don't change it.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Describe the product — materials, size, occasion, etc.",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Price (₹)",
        help_text="Enter the selling price in rupees, e.g. 499",
    )
    stock = models.IntegerField(
        default=0,
        verbose_name="Stock (units available)",
        help_text="How many do you currently have ready to sell? Goes down automatically when ordered.",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Visible on website",
        help_text="Tick this to show the product. Untick to hide it without deleting.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Added On")

    class Meta:
        verbose_name        = "Product"
        verbose_name_plural = "Products"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
        verbose_name="Product",
    )
    image = models.ImageField(
        upload_to='products/gallery/',
        verbose_name="Photo",
        help_text="Upload a clear, well-lit photo. You can add multiple photos per product.",
    )

    class Meta:
        verbose_name        = "Product Photo"
        verbose_name_plural = "Product Photos"

    def __str__(self):
        return f"Photo for {self.product.name}"


class Order(models.Model):
    PAYMENT_METHODS = (
        ('COD', 'Cash on Delivery'),
        ('QR',  'QR Code Transfer'),
    )
    STATUS_CHOICES = (
        ('PENDING',   '⏳ Pending — waiting for your confirmation'),
        ('CONFIRMED', '✅ Confirmed — you have accepted this order'),
        ('SHIPPED',   '🚚 Out for Delivery'),
        ('DELIVERED', '🎉 Delivered — order complete'),
        ('REJECTED',  '❌ Rejected — payment failed or order cancelled'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Customer Account",
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Customer Name",
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name="Phone Number",
    )
    address = models.TextField(
        verbose_name="Delivery Address",
    )
    city = models.CharField(
        max_length=100,
        default='',
        verbose_name="City",
    )
    pincode = models.CharField(
        max_length=10,
        default='',
        verbose_name="Pincode",
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        default='QR',
        verbose_name="Payment Method",
    )
    payment_screenshot = models.ImageField(
        upload_to='payment_proofs/',
        blank=True,
        null=True,
        verbose_name="Payment Screenshot",
        help_text="Screenshot uploaded by the customer as proof of QR payment.",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Total Amount (₹)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Order Status",
        help_text=(
            "Change this to update the order. "
            "The customer will automatically get an email & WhatsApp notification."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ordered On")
    updated_at = models.DateTimeField(auto_now=True,     verbose_name="Last Updated")

    class Meta:
        verbose_name        = "Order"
        verbose_name_plural = "Orders"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} — {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Order",
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Product",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantity",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Price at Purchase (₹)",
        help_text="The price the customer paid — locked at the time of order.",
    )

    class Meta:
        verbose_name        = "Order Item"
        verbose_name_plural = "Order Items"

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity}× {self.product} (Order #{self.order_id})"


class CustomRequest(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Customer Name",
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name="Phone Number",
        help_text="Call or WhatsApp this number to discuss the request.",
    )
    idea_description = models.TextField(
        verbose_name="What They Want",
        help_text="The customer's description of their custom idea.",
    )
    reference_image = models.ImageField(
        upload_to='custom_requests/',
        blank=True,
        null=True,
        verbose_name="Reference Photo",
        help_text="A photo or screenshot the customer uploaded for inspiration.",
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Submitted On",
    )

    class Meta:
        verbose_name        = "Custom Request"
        verbose_name_plural = "Custom Requests"
        ordering            = ['-submitted_at']

    def __str__(self):
        return f"Request from {self.name}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
    )
    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Subscribed On",
    )

    class Meta:
        verbose_name        = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"
        ordering            = ['-subscribed_at']

    def __str__(self):
        return self.email
