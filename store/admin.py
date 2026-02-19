from django.contrib import admin
from .models import Category, Product, ProductImage, CustomRequest, order, OrderItem
from django.utils.safestring import mark_safe

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
    list_editable = ['price', 'stock', 'is_active'] # Allows editing directly in the list
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]  # <--- Connects the gallery to the product page

# 4. Custom Requests Setup (The "Customize Your Ideas" form data)
@admin.register(CustomRequest)
class CustomRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'submitted_at'] # Columns to show in the list
    readonly_fields = ['submitted_at'] # Prevent accidental changing of the date
    list_filter = ['submitted_at'] # Adds a sidebar filter by date

@admin.register(order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    list_editable = ['status']  # Allows changing order status directly from the list view
    search_fields = ['user__username', 'full_name', 'phone_number'] 

    def payment_screenshot_display(self, obj):
        if obj.payment_screenshot:
            return mark_safe(f'<img src="{obj.payment_screenshot.url}" width="300" />')
        return "No Screenshot Uploaded (COD)"