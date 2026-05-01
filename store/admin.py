from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib import messages

from .models import (
    Category, Product, ProductImage,
    CustomRequest, Order, OrderItem, NewsletterSubscriber,
)

# ─────────────────────────────────────────────────────────────────────────────
# Site-wide branding — what she sees at the top of every admin page
# ─────────────────────────────────────────────────────────────────────────────
admin.site.site_header  = "🌸 Happy Heavens — Store Manager"
admin.site.site_title   = "Happy Heavens Admin"
admin.site.index_title  = "Welcome! What would you like to manage today?"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: colour-coded status badge used in Order list
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COLOURS = {
    'PENDING':   ('#b45309', '#fef3c7'),   # amber
    'CONFIRMED': ('#1d4ed8', '#dbeafe'),   # blue
    'SHIPPED':   ('#7c3aed', '#ede9fe'),   # purple
    'DELIVERED': ('#15803d', '#dcfce7'),   # green
    'REJECTED':  ('#b91c1c', '#fee2e2'),   # red
}

def status_badge(status, label):
    colour, bg = STATUS_COLOURS.get(status, ('#374151', '#f3f4f6'))
    return format_html(
        '<span style="background:{bg};color:{colour};padding:3px 10px;'
        'border-radius:12px;font-size:11px;font-weight:600;">{label}</span>',
        bg=bg, colour=colour, label=label,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'product_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    # Friendly field labels & help text shown on the add/edit form
    fieldsets = (
        (None, {
            'fields': ('name', 'slug'),
            'description': (
                '📁 Categories group your products (e.g. "Bouquets", "Hampers"). '
                'The <b>URL Name</b> is filled automatically — you don\'t need to touch it.'
            ),
        }),
    )

    def product_count(self, obj):
        count = obj.products.filter(is_active=True).count()
        return f"{count} product{'s' if count != 1 else ''}"
    product_count.short_description = "Active Products"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────
class ProductImageInline(admin.TabularInline):
    model       = ProductImage
    extra       = 2          # show 2 empty upload slots by default
    max_num     = 10
    verbose_name        = "Photo"
    verbose_name_plural = "📷 Product Photos  (upload as many as you like)"

    fields          = ['image', 'preview']
    readonly_fields = ['preview']

    def preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" width="80" '
                f'style="border-radius:6px;object-fit:cover;height:80px;">'
            )
        return "—"
    preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display        = ['name', 'category', 'price_display', 'stock_display', 'is_active', 'created_at']
    list_editable       = ['is_active']
    list_filter         = ['is_active', 'category']
    search_fields       = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines             = [ProductImageInline]
    list_per_page       = 20
    date_hierarchy      = 'created_at'

    fieldsets = (
        ('📦 Basic Information', {
            'fields': ('name', 'slug', 'category', 'description'),
            'description': (
                'Fill in the product name and description. '
                'The <b>URL Name</b> fills itself automatically.'
            ),
        }),
        ('💰 Price & Stock', {
            'fields': ('price', 'stock'),
            'description': (
                'Set the price in ₹ and how many units you currently have. '
                'Stock goes down automatically when someone orders.'
            ),
        }),
        ('👁️ Visibility', {
            'fields': ('is_active',),
            'description': (
                'Tick <b>Visible on website</b> to show this product to customers. '
                'Untick it to hide the product without deleting it.'
            ),
        }),
    )

    # ── Custom column displays ──────────────────────────────────────────────
    def price_display(self, obj):
        return f"₹{obj.price:,.0f}"
    price_display.short_description = "Price"
    price_display.admin_order_field = "price"

    def stock_display(self, obj):
        if obj.stock == 0:
            return format_html('<span style="color:#b91c1c;font-weight:600;">Out of stock</span>')
        if obj.stock <= 3:
            return format_html('<span style="color:#b45309;font-weight:600;">⚠️ Only {} left</span>', obj.stock)
        return format_html('<span style="color:#15803d;">{} in stock</span>', obj.stock)
    stock_display.short_description = "Stock"
    stock_display.admin_order_field = "stock"


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────────────────
class OrderItemInline(admin.TabularInline):
    model               = OrderItem
    extra               = 0
    can_delete          = False
    verbose_name        = "Item"
    verbose_name_plural = "🛍️ Items in this Order"
    readonly_fields     = ['product', 'quantity', 'price', 'subtotal_display']
    fields              = ['product', 'quantity', 'price', 'subtotal_display']

    def subtotal_display(self, obj):
        return f"₹{obj.subtotal:,.0f}"
    subtotal_display.short_description = "Subtotal"


# ── Bulk actions ────────────────────────────────────────────────────────────
@admin.action(description='✅ Mark selected orders as Confirmed')
def mark_confirmed(modeladmin, request, queryset):
    updated = 0
    for order in queryset:
        if order.status != 'CONFIRMED':
            order.status = 'CONFIRMED'
            order.save(update_fields=['status'])
            updated += 1
    modeladmin.message_user(request, f"{updated} order(s) marked as Confirmed.", messages.SUCCESS)

@admin.action(description='🚚 Mark selected orders as Out for Delivery')
def mark_shipped(modeladmin, request, queryset):
    updated = 0
    for order in queryset:
        if order.status != 'SHIPPED':
            order.status = 'SHIPPED'
            order.save(update_fields=['status'])
            updated += 1
    modeladmin.message_user(request, f"{updated} order(s) marked as Out for Delivery.", messages.SUCCESS)

@admin.action(description='🎉 Mark selected orders as Delivered')
def mark_delivered(modeladmin, request, queryset):
    updated = 0
    for order in queryset:
        if order.status != 'DELIVERED':
            order.status = 'DELIVERED'
            order.save(update_fields=['status'])
            updated += 1
    modeladmin.message_user(request, f"{updated} order(s) marked as Delivered.", messages.SUCCESS)

@admin.action(description='❌ Mark selected orders as Rejected')
def mark_rejected(modeladmin, request, queryset):
    updated = 0
    for order in queryset:
        if order.status != 'REJECTED':
            order.status = 'REJECTED'
            order.save(update_fields=['status'])
            updated += 1
    modeladmin.message_user(request, f"{updated} order(s) marked as Rejected.", messages.SUCCESS)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number',
        'customer_name',
        'customer_phone',
        'total_display',
        'payment_display',
        'status_display',
        'payment_proof_thumb',
        'order_date',
    ]
    list_filter         = ['status', 'payment_method', 'created_at']
    search_fields       = ['full_name', 'phone_number', 'user__username', 'user__email']
    readonly_fields     = [
        'order_number', 'order_date', 'last_updated',
        'customer_info_display', 'payment_proof_large',
    ]
    inlines             = [OrderItemInline]
    actions             = [mark_confirmed, mark_shipped, mark_delivered, mark_rejected]
    list_per_page       = 25
    date_hierarchy      = 'created_at'
    ordering            = ['-created_at']

    fieldsets = (
        ('📋 Order Summary', {
            'fields': ('order_number', 'order_date', 'last_updated', 'status'),
            'description': (
                'Change the <b>Status</b> dropdown below to update this order. '
                'The customer will automatically receive an email & WhatsApp notification.'
            ),
        }),
        ('👤 Customer Details', {
            'fields': ('customer_info_display',),
        }),
        ('💳 Payment', {
            'fields': ('payment_method', 'total_amount', 'payment_proof_large'),
            'description': 'If the customer paid via QR, their payment screenshot appears below.',
        }),
    )

    # ── Column helpers ──────────────────────────────────────────────────────
    def order_number(self, obj):
        return f"#{obj.id}"
    order_number.short_description = "Order"
    order_number.admin_order_field = "id"

    def customer_name(self, obj):
        return obj.full_name
    customer_name.short_description = "Customer Name"
    customer_name.admin_order_field = "full_name"

    def customer_phone(self, obj):
        return format_html(
            '<a href="https://wa.me/91{}" target="_blank" '
            'style="color:#15803d;font-weight:600;">📱 {}</a>',
            obj.phone_number.lstrip('0').lstrip('+91'),
            obj.phone_number,
        )
    customer_phone.short_description = "Phone (tap to WhatsApp)"

    def total_display(self, obj):
        return format_html('<b>₹{}</b>', f"{obj.total_amount:,.0f}")
    total_display.short_description = "Total"
    total_display.admin_order_field = "total_amount"

    def payment_display(self, obj):
        if obj.payment_method == 'QR':
            return format_html('<span style="color:#7c3aed;font-weight:600;">📲 QR Transfer</span>')
        return format_html('<span style="color:#b45309;font-weight:600;">💵 Cash on Delivery</span>')
    payment_display.short_description = "Payment"

    def status_display(self, obj):
        return status_badge(obj.status, obj.get_status_display())
    status_display.short_description = "Status"
    status_display.admin_order_field = "status"

    def payment_proof_thumb(self, obj):
        if obj.payment_screenshot:
            return mark_safe(
                f'<a href="{obj.payment_screenshot.url}" target="_blank">'
                f'<img src="{obj.payment_screenshot.url}" width="50" '
                f'style="border-radius:4px;border:1px solid #e5e7eb;"></a>'
            )
        return format_html('<span style="color:#9ca3af;font-size:11px;">COD / None</span>')
    payment_proof_thumb.short_description = "Payment Proof"

    def order_date(self, obj):
        return obj.created_at.strftime("%d %b %Y, %I:%M %p")
    order_date.short_description = "Ordered On"
    order_date.admin_order_field = "created_at"

    def last_updated(self, obj):
        return obj.updated_at.strftime("%d %b %Y, %I:%M %p")
    last_updated.short_description = "Last Updated"

    def customer_info_display(self, obj):
        return format_html(
            '<table style="border-collapse:collapse;font-size:13px;">'
            '<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Name</td>'
            '<td style="padding:4px 0;font-weight:600;">{}</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Phone</td>'
            '<td style="padding:4px 0;">'
            '<a href="https://wa.me/91{}" target="_blank" style="color:#15803d;">{}</a>'
            '</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Address</td>'
            '<td style="padding:4px 0;">{}, {}, {}</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Account</td>'
            '<td style="padding:4px 0;">{}</td></tr>'
            '</table>',
            obj.full_name,
            obj.phone_number.lstrip('0').lstrip('+91'), obj.phone_number,
            obj.address, obj.city, obj.pincode,
            obj.user.email or obj.user.username,
        )
    customer_info_display.short_description = "Customer"

    def payment_proof_large(self, obj):
        if obj.payment_screenshot:
            return mark_safe(
                f'<a href="{obj.payment_screenshot.url}" target="_blank">'
                f'<img src="{obj.payment_screenshot.url}" width="300" '
                f'style="border-radius:8px;border:1px solid #e5e7eb;margin-top:6px;"></a>'
                f'<br><small style="color:#6b7280;">Click image to open full size</small>'
            )
        return "No payment screenshot (Cash on Delivery order)"
    payment_proof_large.short_description = "Payment Screenshot"


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM REQUESTS
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(CustomRequest)
class CustomRequestAdmin(admin.ModelAdmin):
    list_display    = ['customer_name', 'customer_phone', 'short_idea', 'submitted_on', 'reference_thumb']
    readonly_fields = ['submitted_on', 'reference_image_large']
    list_filter     = ['submitted_at']
    search_fields   = ['name', 'phone_number', 'idea_description']
    list_per_page   = 20
    ordering        = ['-submitted_at']

    fieldsets = (
        ('👤 Customer', {
            'fields': ('name', 'phone_number'),
            'description': 'Contact details of the person who submitted this request.',
        }),
        ('💡 Their Idea', {
            'fields': ('idea_description', 'reference_image_large'),
            'description': (
                'Read what the customer wants. '
                'Call or WhatsApp them on the number above to discuss and confirm.'
            ),
        }),
        ('🕐 Submitted', {
            'fields': ('submitted_on',),
        }),
    )

    def customer_name(self, obj):
        return obj.name
    customer_name.short_description = "Customer Name"
    customer_name.admin_order_field = "name"

    def customer_phone(self, obj):
        return format_html(
            '<a href="https://wa.me/91{}" target="_blank" '
            'style="color:#15803d;font-weight:600;">📱 {}</a>',
            obj.phone_number.lstrip('0').lstrip('+91'),
            obj.phone_number,
        )
    customer_phone.short_description = "Phone (tap to WhatsApp)"

    def short_idea(self, obj):
        text = obj.idea_description
        return text[:80] + "…" if len(text) > 80 else text
    short_idea.short_description = "What They Want"

    def submitted_on(self, obj):
        return obj.submitted_at.strftime("%d %b %Y, %I:%M %p")
    submitted_on.short_description = "Submitted On"

    def reference_thumb(self, obj):
        if obj.reference_image:
            return mark_safe(
                f'<img src="{obj.reference_image.url}" width="60" '
                f'style="border-radius:4px;border:1px solid #e5e7eb;">'
            )
        return format_html('<span style="color:#9ca3af;font-size:11px;">No image</span>')
    reference_thumb.short_description = "Reference Photo"

    def reference_image_large(self, obj):
        if obj.reference_image:
            return mark_safe(
                f'<a href="{obj.reference_image.url}" target="_blank">'
                f'<img src="{obj.reference_image.url}" width="300" '
                f'style="border-radius:8px;border:1px solid #e5e7eb;margin-top:6px;"></a>'
                f'<br><small style="color:#6b7280;">Click to open full size</small>'
            )
        return "No reference image uploaded."
    reference_image_large.short_description = "Reference Photo"


# ─────────────────────────────────────────────────────────────────────────────
# NEWSLETTER SUBSCRIBERS
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display    = ['email', 'subscribed_on']
    readonly_fields = ['subscribed_at']
    search_fields   = ['email']
    list_per_page   = 50
    ordering        = ['-subscribed_at']

    def subscribed_on(self, obj):
        return obj.subscribed_at.strftime("%d %b %Y")
    subscribed_on.short_description = "Subscribed On"
    subscribed_on.admin_order_field = "subscribed_at"
