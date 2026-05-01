from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib import messages
from django import forms

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
    'PENDING':   ('#b45309', '#fef3c7'),
    'CONFIRMED': ('#1d4ed8', '#dbeafe'),
    'SHIPPED':   ('#7c3aed', '#ede9fe'),
    'DELIVERED': ('#15803d', '#dcfce7'),
    'REJECTED':  ('#b91c1c', '#fee2e2'),
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
# PRODUCTS — multi-upload image inline
# ─────────────────────────────────────────────────────────────────────────────

class MultipleFileInput(forms.ClearableFileInput):
    """
    A file input widget that accepts multiple files at once.
    Renders with the `multiple` HTML attribute so the OS file picker
    lets the user select several images in one go.
    """
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        final_attrs = {'multiple': True, 'accept': 'image/*'}
        if attrs:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)


class MultipleImageField(forms.ImageField):
    """
    An ImageField that returns a list of uploaded files instead of one.
    Used on the "Upload new photos" row of the inline.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # data is a list when multiple files are submitted
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        result = []
        for f in data:
            result.append(super().clean(f, initial))
        return result


class ProductImageUploadForm(forms.Form):
    """
    A standalone form with a single multi-file field.
    This is NOT a ModelForm — it only handles the upload action.
    The actual ProductImage records are created in save_formset.
    """
    new_photos = MultipleImageField(
        required=False,
        label='Upload new photos',
        help_text=(
            'Hold <b>Ctrl</b> (Windows) or <b>⌘ Cmd</b> (Mac) while clicking '
            'to select multiple photos at once.'
        ),
    )


class ProductImageInline(admin.TabularInline):
    """
    Shows existing images as a grid with previews + delete checkboxes.
    A separate upload row at the bottom handles multi-file upload.
    """
    model               = ProductImage
    extra               = 0          # no blank rows — upload handled separately
    max_num             = 20
    can_delete          = True
    verbose_name        = "Photo"
    verbose_name_plural = "📷 Product Photos"
    fields              = ['image', 'preview']
    readonly_fields     = ['preview']

    def preview(self, obj):
        if obj.pk and obj.image:
            try:
                url = obj.image.url
                return mark_safe(
                    f'<a href="{url}" target="_blank" title="Click to open full size">'
                    f'<img src="{url}" '
                    f'style="width:90px;height:90px;object-fit:cover;border-radius:8px;'
                    f'border:2px solid #e5e7eb;display:block;" '
                    f'onerror="this.style.border=\'2px solid #ef4444\';'
                    f'this.title=\'⚠️ Image broken or missing\';">'
                    f'</a>'
                    f'<div style="font-size:10px;color:#6b7280;margin-top:3px;text-align:center;">'
                    f'Click to open</div>'
                )
            except Exception:
                return mark_safe(
                    '<span style="color:#ef4444;font-size:11px;">⚠️ Image unavailable</span>'
                )
        return mark_safe('<span style="color:#9ca3af;font-size:11px;">—</span>')
    preview.short_description = "Preview"

    class Media:
        # Inject a small CSS + JS block into the admin page for the upload zone
        css = {'all': []}
        js  = []


class MultiUploadWidget(forms.Widget):
    """
    Renders a styled drag-and-drop upload zone with a multi-file input
    and a live JS preview grid that shows thumbnails before saving.
    """
    def render(self, name, value, attrs=None, renderer=None):
        input_id = f'id_{name}'
        return f"""
<div id="upload-zone-wrapper" style="margin:12px 0;">

  <!-- Drop zone -->
  <label for="{input_id}"
         id="upload-drop-zone"
         style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                gap:8px;padding:28px 20px;border:2px dashed #d1d5db;border-radius:12px;
                background:#f9fafb;cursor:pointer;transition:border-color .2s,background .2s;"
         onmouseover="this.style.borderColor='#fb7185';this.style.background='#fff1f2';"
         onmouseout="this.style.borderColor='#d1d5db';this.style.background='#f9fafb';">
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="none"
         viewBox="0 0 24 24" stroke="#9ca3af" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
    </svg>
    <span style="font-size:13px;font-weight:600;color:#374151;">
      Click to select photos &nbsp;or&nbsp; drag &amp; drop here
    </span>
    <span style="font-size:11px;color:#9ca3af;">
      Hold Ctrl / ⌘ Cmd to select multiple files at once &nbsp;·&nbsp; JPG, PNG, WEBP
    </span>
    <input id="{input_id}" name="{name}" type="file"
           multiple accept="image/*"
           style="display:none;"
           onchange="hhPreviewImages(this)">
  </label>

  <!-- Live preview grid — populated by JS before save -->
  <div id="upload-preview-grid"
       style="display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;"></div>

  <p id="upload-count-label"
     style="font-size:11px;color:#6b7280;margin-top:6px;display:none;">
  </p>

</div>

<script>
function hhPreviewImages(input) {{
  var grid  = document.getElementById('upload-preview-grid');
  var label = document.getElementById('upload-count-label');
  grid.innerHTML = '';

  var files = Array.from(input.files);
  if (!files.length) {{ label.style.display='none'; return; }}

  label.style.display = 'block';
  label.textContent   = files.length + ' photo' + (files.length > 1 ? 's' : '') + ' selected — check previews below, then click Save:';

  files.forEach(function(file, idx) {{
    var wrapper = document.createElement('div');
    wrapper.style.cssText = 'position:relative;width:90px;';

    var img = document.createElement('img');
    img.style.cssText = 'width:90px;height:90px;object-fit:cover;border-radius:8px;'
                      + 'border:2px solid #e5e7eb;display:block;';
    img.alt = file.name;

    // Show broken-image indicator if file can't be read
    img.onerror = function() {{
      this.style.border = '2px solid #ef4444';
      badge.textContent = '⚠️';
      badge.style.background = '#ef4444';
    }};

    var reader = new FileReader();
    reader.onload = function(e) {{ img.src = e.target.result; }};
    reader.readAsDataURL(file);

    // Small filename label
    var name = document.createElement('div');
    name.style.cssText = 'font-size:9px;color:#6b7280;margin-top:3px;'
                       + 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'
                       + 'max-width:90px;text-align:center;';
    name.textContent = file.name;

    // Index badge
    var badge = document.createElement('span');
    badge.style.cssText = 'position:absolute;top:4px;left:4px;background:#111827;color:#fff;'
                        + 'font-size:9px;font-weight:700;padding:1px 5px;border-radius:6px;';
    badge.textContent = idx + 1;

    wrapper.appendChild(img);
    wrapper.appendChild(badge);
    wrapper.appendChild(name);
    grid.appendChild(wrapper);
  }});
}}
</script>
"""

    def value_from_datadict(self, data, files, name):
        # Return the list of uploaded files
        return files.getlist(name)


class MultiUploadField(forms.Field):
    widget = MultiUploadWidget

    def clean(self, value):
        if not value:
            return []
        cleaned = []
        for f in value:
            # Basic image validation
            if not f.content_type.startswith('image/'):
                raise forms.ValidationError(f'"{f.name}" is not an image file.')
            cleaned.append(f)
        return cleaned


class ProductAdminForm(forms.ModelForm):
    """
    Extends the standard Product form with the multi-upload field.
    The field is not a model field — it's handled in save_formset / save_model.
    """
    upload_photos = MultiUploadField(
        required=False,
        label='📷 Upload New Photos',
        help_text=(
            'Select multiple photos at once. '
            'Previews appear immediately so you can check them before saving.'
        ),
    )

    class Meta:
        model  = Product
        fields = '__all__'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form                = ProductAdminForm
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
        ('📷 Upload New Photos', {
            'fields': ('upload_photos',),
            'description': (
                'Select multiple photos at once using the upload zone below. '
                'Existing photos are shown in the <b>Product Photos</b> section above — '
                'tick <b>Delete</b> next to any photo you want to remove.'
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Save the product first, then attach any uploaded images."""
        super().save_model(request, obj, form, change)
        uploaded_files = form.cleaned_data.get('upload_photos') or []
        for f in uploaded_files:
            ProductImage.objects.create(product=obj, image=f)

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
        ('📝 Your Private Notes', {
            'fields': ('notes',),
            'description': (
                'Write anything here for yourself — e.g. "Called customer, delivering Friday". '
                '<b>Customers never see this.</b>'
            ),
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
