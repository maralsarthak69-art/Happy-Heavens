# Implementation Plan: Happy Heavens E-Commerce Redesign

## Overview

Incremental hardening of the existing Django 4.2 / PostgreSQL monolith. Tasks are ordered so each step builds on the previous: data models first, then business logic, then views/templates, then admin, then security/infra. All changes stay within the existing `store` app and `core` settings unless noted.

## Tasks

- [x] 1. Harden production security configuration
  - In `core/settings.py`, add environment-conditional security settings block: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF`
  - Replace wildcard `ALLOWED_HOSTS = ['*']` with `ALLOWED_HOSTS = [env('ALLOWED_HOST')]` gated on `not DEBUG`
  - Verify all secrets (`SECRET_KEY`, `DATABASE_URL`, Cloudinary credentials) are loaded exclusively via `django-environ`; remove any hardcoded values
  - Set `conn_max_age=600` in the `dj-database-url` database config
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 12.5_

- [x] 2. Update data models and generate migrations
  - [x] 2.1 Rename `order` model class to `Order` (PEP 8); update all references in `store/views.py`, `store/admin.py`, `store/signals.py`, and existing migrations
    - _Requirements: 2.1_
  - [x] 2.2 Add `city` and `pincode` `CharField` fields to `Order`; add `Meta.indexes` on `Order.status` and `Order.created_at`
    - _Requirements: 2.2, 2.7_
  - [x] 2.3 Change `OrderItem.product` `on_delete` from `CASCADE` to `SET_NULL` with `null=True, blank=True`; confirm `OrderItem.price` has no `auto_now` or update logic
    - _Requirements: 2.4, 2.6_
  - [x] 2.4 Add `Meta.indexes` on `Product.is_active` and `Product.category`; add `__str__` methods to all models that lack them (`Order`, `OrderItem`, `Product`, `Category`, `ProductImage`, `CustomRequest`)
    - _Requirements: 2.3, 2.5_
  - [x] 2.5 Generate and apply a single consolidated migration covering all model changes above
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  - [ ]* 2.6 Write property test for OrderItem price lock (Property 12)
    - **Property 12: OrderItem price is locked at order creation**
    - **Validates: Requirements 2.4**
  - [ ]* 2.7 Write property test for product deletion sets OrderItem.product to NULL (Property 13)
    - **Property 13: Product deletion sets OrderItem.product to NULL**
    - **Validates: Requirements 2.6**

- [x] 3. Implement Inventory Manager
  - [x] 3.1 In `store/views.py` `add_to_cart` view, add a stock check: if `product.stock == 0`, return an error message and do not call `cart.add()`; add "Out of Stock" context flag used in product listing and detail templates
    - _Requirements: 3.1, 3.5_
  - [x] 3.2 In `checkout_view`, wrap order creation in `transaction.atomic()`; use `select_for_update()` to re-validate each cart item's quantity against current `Product.stock`; raise `InsufficientStockError` (custom exception) if any item exceeds stock, preserving cart and returning field-level errors
    - _Requirements: 3.2, 3.3_
  - [x] 3.3 On successful stock validation, atomically decrement `Product.stock` by ordered quantity using `product.save(update_fields=['stock'])`
    - _Requirements: 3.4_
  - [ ]* 3.4 Write property test for out-of-stock add-to-cart (Property 1)
    - **Property 1: Out-of-stock products cannot be added to cart**
    - **Validates: Requirements 3.1**
  - [ ]* 3.5 Write property test for checkout stock validation prevents overselling (Property 2)
    - **Property 2: Checkout stock validation prevents overselling**
    - **Validates: Requirements 3.2, 3.3**
  - [ ]* 3.6 Write property test for atomic stock decrement on confirmed order (Property 3)
    - **Property 3: Atomic stock decrement on confirmed order**
    - **Validates: Requirements 3.4**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Extend Cart with quantity control and stale-item cleanup
  - [x] 5.1 Add `update(product, quantity)` method to `store/cart.py`: sets quantity directly; removes item if `quantity <= 0`
    - _Requirements: 4.1, 4.2_
  - [x] 5.2 Update `Cart.__iter__` to filter out products where `is_active=False`, flag them for removal, and expose a `removed_items` list for template notification
    - _Requirements: 4.5_
  - [x] 5.3 Confirm `SESSION_COOKIE_AGE = 604800` (7 days) is set in `core/settings.py`
    - _Requirements: 4.6_
  - [x] 5.4 Update cart summary template to display per-item subtotal (`price × quantity`) and overall cart total
    - _Requirements: 4.3_
  - [x] 5.5 Update `add_to_cart` view to increment existing item quantity by 1 rather than creating a duplicate entry (verify `cart.add()` logic)
    - _Requirements: 4.4_
  - [ ]* 5.6 Write property test for cart quantity update round trip (Property 4)
    - **Property 4: Cart quantity update round trip**
    - **Validates: Requirements 4.1, 4.2**
  - [ ]* 5.7 Write property test for cart total equals sum of line totals (Property 5)
    - **Property 5: Cart total equals sum of line totals**
    - **Validates: Requirements 4.3**
  - [ ]* 5.8 Write property test for duplicate add increments quantity (Property 6)
    - **Property 6: Duplicate add increments quantity**
    - **Validates: Requirements 4.4**

- [x] 6. Implement checkout and payment workflow
  - [x] 6.1 Update `CheckoutForm` in `store/forms.py` to include `city` and `pincode` fields with required validation; strip whitespace in `clean_*` methods for all required text fields
    - _Requirements: 5.1, 5.6_
  - [x] 6.2 In `checkout_view`, add QR/COD branching: if `payment_method == 'QR'` and `request.FILES.get('payment_screenshot')` is absent, add a form error and re-render with preserved POST values
    - _Requirements: 5.2, 5.3_
  - [x] 6.3 On successful order creation, redirect to a `order_success` view that renders a confirmation page with Order ID, items, total, and payment method; use `@login_required(login_url='/login/?next=/checkout/')` on `checkout_view`
    - _Requirements: 5.4, 5.5_
  - [ ]* 6.4 Write property test for checkout form rejects incomplete required fields (Property 8)
    - **Property 8: Checkout form rejects incomplete or whitespace-only required fields**
    - **Validates: Requirements 5.1, 5.6**
  - [ ]* 6.5 Write property test for QR payment requires screenshot (Property 9)
    - **Property 9: QR payment requires screenshot**
    - **Validates: Requirements 5.2**
  - [ ]* 6.6 Write unit tests for checkout flow: COD order created with `status='PENDING'`, cart cleared after success, unauthenticated redirect
    - _Requirements: 5.3, 5.4, 5.5_

- [x] 7. Implement customer order history and detail views
  - [x] 7.1 Create/update `order_list` view: filter `Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')`, paginate at 10 per page; render `order_list.html`
    - _Requirements: 6.1, 6.2_
  - [x] 7.2 Create/update `order_detail` view: fetch Order by `pk`, assert `order.user == request.user` (return 403 otherwise); render `order_detail.html` with all OrderItems (product name, quantity, unit price, subtotal)
    - _Requirements: 6.3, 6.5_
  - [ ]* 7.3 Write property test for order history scoped to requesting user (Property 11)
    - **Property 11: Order history is scoped to the requesting user**
    - **Validates: Requirements 6.1, 6.5**

- [x] 8. Implement Notification Service
  - [x] 8.1 Create `store/signals.py` (or extend existing): add `post_save` signal on `Order` that calls `send_mail` when `status` changes; add `post_save` signal on `CustomRequest` that emails the store owner
    - _Requirements: 6.4, 7.4, 10.4_
  - [x] 8.2 Configure `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` via env vars in `core/settings.py`
    - _Requirements: 6.4_
  - [ ]* 8.3 Write unit test for order status change triggers email notification
    - _Requirements: 6.4, 7.4_

- [x] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement product and category management improvements
  - [x] 10.1 Update `ProductAdmin` and `CategoryAdmin` in `store/admin.py` to use `prepopulated_fields = {'slug': ('name',)}`; add `ProductImageInline` as `TabularInline` on `ProductAdmin`; add `list_editable = ['stock']` to `ProductAdmin`
    - _Requirements: 8.1, 8.3, 3.6_
  - [x] 10.2 Update product listing and detail templates to display the first `ProductImage` as the primary thumbnail; add a placeholder image fallback when `product.images.all()` is empty
    - _Requirements: 8.4, 8.5_
  - [x] 10.3 Update product detail URL in `store/urls.py` to `path('product/<slug:slug>/', product_detail, name='product_detail')`; update `product_detail` view to use `get_object_or_404(Product, slug=slug)`; add a compatibility redirect view for old PK-based URLs
    - _Requirements: 8.7_
  - [ ]* 10.4 Write property test for inactive products excluded from all listings (Property 7)
    - **Property 7: Inactive products are excluded from all listings**
    - **Validates: Requirements 8.2, 9.1, 9.4**

- [x] 11. Implement Search Engine
  - [x] 11.1 Update `search` view in `store/views.py` to use `Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query)` filtered by `is_active=True`, with `.select_related('category').prefetch_related('images')`; paginate at 12 per page; pass result count to template
    - _Requirements: 9.1, 9.2, 9.3, 9.5_
  - [x] 11.2 Update `search.html` template to display result count and a "no results" message with category browse suggestion when `results` is empty
    - _Requirements: 9.2, 9.3_
  - [x] 11.3 Update category page view to filter `is_active=True` products and paginate at 12 per page
    - _Requirements: 9.4, 9.5_
  - [ ]* 11.4 Write property test for search results match query in name, description, or category (Property 10)
    - **Property 10: Search results match query in name, description, or category**
    - **Validates: Requirements 9.1, 9.4**

- [x] 12. Implement Admin order management
  - [x] 12.1 Update `OrderAdmin` in `store/admin.py`: set `list_display` to include Order ID, customer username, total amount, payment method, status, payment proof thumbnail, and creation date; add `list_filter` for `status`, `payment_method`, `created_at`; add `search_fields` for `user__username`, `full_name`, `phone_number`
    - _Requirements: 7.1, 7.2, 7.6_
  - [x] 12.2 Add `OrderItemInline` as `TabularInline` on `OrderAdmin`; add a `bulk_update_status` custom admin action that updates selected Orders' `status` field
    - _Requirements: 7.3, 7.5_
  - [x] 12.3 Update `CustomRequestAdmin`: set `list_display` to include customer name, phone number, submission date, and reference image thumbnail; add `list_filter` for `submitted_at`
    - _Requirements: 10.5_
  - [ ]* 12.4 Write unit test for bulk status update action triggers notification signal
    - _Requirements: 7.3, 7.4_

- [x] 13. Implement Custom Request form and view
  - [x] 13.1 Update `CustomRequestForm` in `store/forms.py` to validate `name`, `phone_number`, and `idea_description` as non-empty (strip whitespace); update `custom_request` view to save on valid POST, redirect to success page, and re-render with preserved values and field errors on failure
    - _Requirements: 10.1, 10.2, 10.3_
  - [ ]* 13.2 Write property test for custom request form rejects empty required fields (Property 15)
    - **Property 15: Custom request form rejects empty required fields**
    - **Validates: Requirements 10.2, 10.3**

- [x] 14. Implement User Authentication improvements
  - [x] 14.1 Update `SignupForm` in `store/forms.py` to enforce minimum 8-character password and reject all-numeric passwords using Django's `MinimumLengthValidator` and `NumericPasswordValidator`; update signup view to auto-login on success and re-render with field errors on failure
    - _Requirements: 11.1, 11.2, 11.6_
  - [x] 14.2 Update login view to redirect to `next` parameter on success; return a non-specific error message on invalid credentials; update logout view to invalidate session and redirect to home
    - _Requirements: 11.3, 11.4, 11.5_
  - [ ]* 14.3 Write property test for signup rejects invalid passwords (Property 14)
    - **Property 14: Signup rejects invalid passwords**
    - **Validates: Requirements 11.2, 11.6**

- [x] 15. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Query optimization
  - [x] 16.1 Audit all list views (`home`, `category`, `order_list`, `search`) and add `select_related` / `prefetch_related` calls to eliminate N+1 patterns; verify home page renders in ≤ 5 queries using Django's `assertNumQueries` in a test
    - _Requirements: 12.1, 12.2_

- [x] 17. Error handling and custom error pages
  - [x] 17.1 Create branded `templates/404.html`, `templates/403.html`, and `templates/500.html` using TailwindCSS and Happy Heavens typography; register `handler404`, `handler403`, `handler500` in `core/urls.py`
    - _Requirements: 13.1, 13.4_
  - [x] 17.2 Audit all views to replace bare `Product.objects.get()` / `Category.objects.get()` calls with `get_object_or_404`; confirm all URL patterns use typed converters (`<int:pk>`, `<slug:slug>`) so non-matching values return 404 automatically
    - _Requirements: 13.2, 13.5_
  - [ ]* 17.3 Write unit tests for 404 on missing product/category, 403 on wrong-user order access, and 500 template rendering
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 18. Static files, media pipeline, and deployment configuration
  - [x] 18.1 Set `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'` in production settings; confirm `whitenoise.middleware.WhiteNoiseMiddleware` is in `MIDDLEWARE`
    - _Requirements: 12.3_
  - [x] 18.2 Confirm Cloudinary storage backend is active in production (`DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'`) and local dev falls back to `FileSystemStorage`
    - _Requirements: 8.6, 12.4_
  - [x] 18.3 Verify `Procfile` specifies `web: gunicorn core.wsgi:application`; verify `build.sh` runs `python manage.py collectstatic --noinput` and `python manage.py migrate`; verify `Dockerfile` uses a non-root user and production gunicorn command
    - _Requirements: 14.1, 14.2, 14.5, 14.6_
  - [x] 18.4 Confirm `dj-database-url` parses `DATABASE_URL` env var and `django-environ` loads `.env` in local dev; confirm `.env` is in `.gitignore`
    - _Requirements: 14.3, 14.4_

- [x] 19. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Property tests use `hypothesis` with `@settings(max_examples=100)`; mock Cloudinary with `override_settings(DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage')`
- Each task references specific requirements for traceability
- Checkpoints at tasks 4, 9, 15, and 19 ensure incremental validation
