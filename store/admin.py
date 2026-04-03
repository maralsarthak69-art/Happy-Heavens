from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage, CustomRequest, Order, OrderItem

# 1. Image Gallery Setup
# This allows you to upload multiple images INSIDE the Product page
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Number of empty upload slots to show by default

# 2. Category Setup
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

# 3. Product Setup (With Gallery attached)
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'category', 'is_active']
    list_editable = ['price', 'stock', 'is_active']  # Allows editing directly in the list
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]  # Connects the gallery to the product page

# 4. OrderItem inline for Order detail page
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']
    fields = ['product', 'quantity', 'price']
    can_delete = False

# 5. Bulk status update action — iterates and calls .save() so post_save signals fire
@admin.action(description='Mark selected orders as CONFIRMED')
def bulk_update_status(modeladmin, request, queryset):
    for order in queryset:
        if order.status != 'CONFIRMED':
            order.status = 'CONFIRMED'
            order.save(update_fields=['status'])

# 6. Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_customer_username',
        'total_amount',
        'payment_method',
        'status',
        'payment_screenshot_display',
        'created_at',
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['user__username', 'full_name', 'phone_number']
    readonly_fields = ['payment_screenshot_display']
    inlines = [OrderItemInline]
    actions = [bulk_update_status]

    def get_customer_username(self, obj):
        return obj.user.username
    get_customer_username.short_description = 'Customer'
    get_customer_username.admin_order_field = 'user__username'

    def payment_screenshot_display(self, obj):
        if obj.payment_screenshot:
            return mark_safe(f'<img src="{obj.payment_screenshot.url}" width="100" style="border-radius: 5px;"/>')
        return "COD / No Proof"
    payment_screenshot_display.short_description = 'Payment Proof'

# 7. Custom Requests Setup
@admin.register(CustomRequest)
class CustomRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'submitted_at', 'reference_image_thumbnail']
    readonly_fields = ['submitted_at', 'reference_image_thumbnail']
    list_filter = ['submitted_at']

    def reference_image_thumbnail(self, obj):
        if obj.reference_image:
            return mark_safe(f'<img src="{obj.reference_image.url}" width="80" style="border-radius: 4px;"/>')
        return "No Image"
    reference_image_thumbnail.short_description = 'Reference Image'
