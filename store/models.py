from django.db import models
from django.contrib.auth.models import User

class Order(models.Model):
    PAYMENT_METHODS = (
        ('COD', 'Cash on Delivery'),
        ('QR', 'QR Code Transfer'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('REJECTED', 'Payment Failed/Rejected')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()

    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='QR')
    payment_screenshot = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    city = models.CharField(max_length=100, default='')
    pincode = models.CharField(max_length=10, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"OrderItem {self.id} (Order #{self.order_id})"

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True) 

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
class CustomRequest(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, help_text="So we can contact you on WhatsApp")
    idea_description = models.TextField(help_text="Describe the colors, flowers, or theme you want.")
    reference_image = models.ImageField(upload_to='custom_requests/', blank=True, null=True, help_text="Upload a screenshot or photo of what you want.")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CustomRequest from {self.name}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email