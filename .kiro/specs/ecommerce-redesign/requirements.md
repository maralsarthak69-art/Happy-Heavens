# Requirements Document

## Introduction

Happy Heavens is a handcrafted gifting e-commerce brand based in Pune, India. The existing system is a Django/PostgreSQL monolith with session-based cart, manual QR/COD payment workflow, Cloudinary media storage, and a TailwindCSS frontend. The goal of this redesign is to evolve the platform into a scalable, production-ready system — hardening the architecture, improving the customer experience, adding operational tooling, and establishing a foundation for future growth — while preserving the brand's luxury aesthetic.

The stack remains: HTML, TailwindCSS, JavaScript, Django 4.2, and PostgreSQL.

---

## Glossary

- **Store**: The Django application (`store`) that handles all customer-facing e-commerce logic.
- **Admin**: The Django admin interface used by the store owner to manage products, orders, and customers.
- **Cart**: The session-based shopping cart that holds items before checkout.
- **Order**: A confirmed purchase record stored in the database, linked to a User.
- **OrderItem**: A line item within an Order, referencing a Product, quantity, and locked price.
- **Product**: A sellable item with a name, price, stock count, category, and image gallery.
- **Category**: A grouping of Products (e.g., "Bouquets", "Gift Hampers").
- **CustomRequest**: A customer-submitted form requesting a bespoke/custom product.
- **User**: A registered customer account backed by Django's built-in `auth.User`.
- **Payment_Processor**: The component responsible for handling payment method selection, QR proof upload, and COD flow.
- **Inventory_Manager**: The component responsible for tracking and enforcing product stock levels.
- **Search_Engine**: The component responsible for querying products by name, description, and category.
- **Notification_Service**: The component responsible for sending order status updates to customers and the store owner.
- **Security_Layer**: The middleware and configuration responsible for enforcing HTTPS, CSRF, rate limiting, and input validation.
- **Media_Pipeline**: The component responsible for uploading, storing, and serving product images via Cloudinary.
- **Slug**: A URL-friendly string identifier derived from a model's name field.

---

## Requirements

### Requirement 1: Secure Configuration and Environment Hardening

**User Story:** As a store owner, I want the production environment to be securely configured, so that customer data and the application are protected from common vulnerabilities.

#### Acceptance Criteria

1. THE Security_Layer SHALL enforce HTTPS-only access in production by setting `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, and `SESSION_COOKIE_SECURE` to their secure values.
2. THE Security_Layer SHALL restrict `ALLOWED_HOSTS` to explicitly defined hostnames in production, replacing the current wildcard `'*'` value.
3. THE Security_Layer SHALL store all secrets (SECRET_KEY, DATABASE_URL, Cloudinary credentials) exclusively in environment variables and never in version-controlled files.
4. WHEN `DEBUG` is set to `False`, THE Security_Layer SHALL serve no debug tracebacks or internal error details to the client.
5. THE Security_Layer SHALL set `X_FRAME_OPTIONS` to `DENY` and enable `SECURE_CONTENT_TYPE_NOSNIFF` in production.

---

### Requirement 2: Robust Data Models

**User Story:** As a developer, I want the database models to be well-structured and consistent, so that data integrity is maintained as the platform scales.

#### Acceptance Criteria

1. THE Store SHALL rename the `order` model class to `Order` to follow Python class naming conventions, updating all references in views, admin, and migrations.
2. THE Store SHALL add a `db_index=True` index on `Order.status` and `Order.created_at` to support efficient admin filtering queries.
3. THE Store SHALL add a `db_index=True` index on `Product.is_active` and `Product.category` to support efficient storefront queries.
4. THE Store SHALL enforce that `OrderItem.price` captures the product's price at the time of purchase and is never updated after order creation.
5. THE Store SHALL add a `__str__` method to all models that returns a human-readable string uniquely identifying the instance.
6. WHEN a `Product` is deleted, THE Store SHALL set the corresponding `OrderItem.product` field to `NULL` rather than cascading the delete, preserving historical order records.
7. THE Store SHALL add a `city` and `pincode` field to the `Order` model to support delivery logistics.

---

### Requirement 3: Inventory Management

**User Story:** As a store owner, I want stock levels to be enforced at checkout, so that customers cannot order products that are out of stock.

#### Acceptance Criteria

1. WHEN a customer attempts to add a product to the Cart and the product's `stock` is `0`, THE Inventory_Manager SHALL prevent the item from being added and return an error message to the customer.
2. WHEN a customer submits a checkout form, THE Inventory_Manager SHALL verify that the requested quantity for each OrderItem does not exceed the available `Product.stock` at the time of submission.
3. IF the stock check at checkout fails for any item, THEN THE Inventory_Manager SHALL reject the order, preserve the cart contents, and display a specific error message identifying the out-of-stock item.
4. WHEN an Order is confirmed, THE Inventory_Manager SHALL atomically decrement the `Product.stock` by the ordered quantity using a database transaction to prevent race conditions.
5. WHILE a product's `stock` is `0`, THE Store SHALL display an "Out of Stock" indicator on the product listing and detail pages.
6. THE Admin SHALL allow the store owner to update `Product.stock` directly from the product list view in the Django admin.

---

### Requirement 4: Cart Reliability and Quantity Control

**User Story:** As a customer, I want to manage item quantities in my cart, so that I can adjust my order before checkout.

#### Acceptance Criteria

1. THE Cart SHALL support incrementing and decrementing the quantity of an existing item without removing and re-adding it.
2. WHEN a customer sets an item's quantity to `0` in the cart, THE Cart SHALL remove that item from the cart automatically.
3. THE Cart SHALL display the per-item subtotal (price × quantity) and the overall cart total on the cart summary page.
4. WHEN a customer adds a product to the Cart that already exists in the Cart, THE Cart SHALL increment the existing item's quantity by `1` rather than creating a duplicate entry.
5. IF a product in the Cart is deactivated (`is_active=False`) before checkout, THEN THE Cart SHALL remove that item and notify the customer on the next cart page load.
6. THE Cart SHALL persist across browser sessions for authenticated users by associating cart data with the user's session for a minimum of 7 days.

---

### Requirement 5: Checkout and Payment Workflow

**User Story:** As a customer, I want a clear and reliable checkout process, so that I can place orders with confidence.

#### Acceptance Criteria

1. WHEN a customer submits the checkout form, THE Payment_Processor SHALL validate that `full_name`, `phone_number`, `address`, `city`, and `pincode` fields are non-empty before creating an Order.
2. IF the customer selects "QR Code Transfer" as the payment method, THEN THE Payment_Processor SHALL require a `payment_screenshot` image upload and reject the submission if no file is provided.
3. IF the customer selects "Cash on Delivery" as the payment method, THEN THE Payment_Processor SHALL not require a `payment_screenshot` and SHALL create the Order with `status='PENDING'`.
4. WHEN an Order is successfully created, THE Store SHALL redirect the customer to a unique order confirmation page displaying the Order ID, items, total, and payment method.
5. THE Store SHALL prevent unauthenticated users from accessing the checkout page and SHALL redirect them to the login page with a `next` parameter pointing back to checkout.
6. WHEN a checkout form submission fails validation, THE Store SHALL re-render the checkout page with the submitted field values preserved and specific error messages displayed.

---

### Requirement 6: Order Management for Customers

**User Story:** As a customer, I want to view my order history and track order status, so that I know the state of my purchases.

#### Acceptance Criteria

1. THE Store SHALL display a paginated list of all Orders belonging to the authenticated user, ordered by `created_at` descending, with a maximum of 10 orders per page.
2. WHEN viewing the order list, THE Store SHALL display the Order ID, creation date, total amount, payment method, and current status for each Order.
3. THE Store SHALL provide a dedicated order detail page showing all OrderItems (product name, quantity, unit price, subtotal) for a given Order.
4. WHEN an Order's `status` changes, THE Notification_Service SHALL send an email notification to the customer's registered email address containing the Order ID and new status.
5. THE Store SHALL prevent a customer from accessing the order detail page of an Order that does not belong to them, returning a 403 response.

---

### Requirement 7: Order Management for Admin

**User Story:** As a store owner, I want a powerful admin interface for managing orders, so that I can efficiently process and fulfill customer purchases.

#### Acceptance Criteria

1. THE Admin SHALL display Orders in a list with columns for Order ID, customer username, total amount, payment method, status, payment proof thumbnail, and creation date.
2. THE Admin SHALL allow the store owner to filter Orders by `status`, `payment_method`, and `created_at` date range.
3. THE Admin SHALL allow the store owner to update the `status` of multiple Orders simultaneously using a bulk action.
4. WHEN the store owner changes an Order's `status` to `CONFIRMED`, THE Notification_Service SHALL trigger an email to the customer.
5. THE Admin SHALL display all OrderItems inline within the Order detail page, showing product name, quantity, and price.
6. THE Admin SHALL allow the store owner to search Orders by customer username, full name, or phone number.

---

### Requirement 8: Product and Category Management

**User Story:** As a store owner, I want to manage products and categories efficiently, so that the storefront always reflects current inventory and offerings.

#### Acceptance Criteria

1. THE Admin SHALL auto-populate the `slug` field from the `name` field for both Product and Category models.
2. WHEN a product's `is_active` field is set to `False`, THE Store SHALL exclude that product from all storefront listings, category pages, and search results.
3. THE Admin SHALL allow the store owner to upload multiple images for a single Product using an inline gallery interface.
4. THE Store SHALL display the first image in a Product's gallery as the primary thumbnail on listing pages.
5. IF a Product has no images, THEN THE Store SHALL display a placeholder image on listing and detail pages.
6. THE Media_Pipeline SHALL upload all product images to Cloudinary in production and serve them via Cloudinary CDN URLs.
7. THE Store SHALL support product slugs as URL identifiers in addition to primary keys, using `Product.slug` in the product detail URL.

---

### Requirement 9: Search and Discovery

**User Story:** As a customer, I want to search and browse products effectively, so that I can find what I'm looking for quickly.

#### Acceptance Criteria

1. WHEN a customer submits a search query, THE Search_Engine SHALL return Products matching the query against `name`, `description`, and `category__name` fields using case-insensitive partial matching.
2. WHEN a search query returns no results, THE Search_Engine SHALL display a "no results found" message and suggest browsing by category.
3. THE Store SHALL display the total number of results on the search results page.
4. WHEN a customer navigates to a category page, THE Store SHALL display only active products (`is_active=True`) belonging to that category.
5. THE Store SHALL support pagination on category pages and the search results page, displaying a maximum of 12 products per page.

---

### Requirement 10: Custom Request (Bespoke Orders)

**User Story:** As a customer, I want to submit a custom product request with a reference image, so that I can order a personalized gift.

#### Acceptance Criteria

1. WHEN a customer submits the custom request form with valid data, THE Store SHALL save the CustomRequest to the database and display a success confirmation page.
2. THE Store SHALL validate that `name`, `phone_number`, and `idea_description` are non-empty before saving a CustomRequest.
3. IF the custom request form submission fails validation, THEN THE Store SHALL re-render the form with the submitted values preserved and specific field-level error messages displayed.
4. WHEN a CustomRequest is submitted, THE Notification_Service SHALL send an email alert to the store owner's configured email address containing the customer's name, phone number, and idea description.
5. THE Admin SHALL display CustomRequests with columns for customer name, phone number, submission date, and a thumbnail of the reference image if provided.

---

### Requirement 11: User Authentication and Account Management

**User Story:** As a customer, I want to register, log in, and manage my account, so that I can track orders and have a personalized experience.

#### Acceptance Criteria

1. WHEN a customer submits the signup form with a unique username and matching passwords, THE Store SHALL create a new User account and log the customer in automatically.
2. IF the signup form contains a duplicate username or mismatched passwords, THEN THE Store SHALL re-render the signup page with specific field-level error messages.
3. WHEN a customer submits valid credentials on the login form, THE Store SHALL authenticate the user and redirect to the `next` URL parameter if present, otherwise to the home page.
4. IF a customer submits invalid credentials, THEN THE Store SHALL re-render the login page with a non-specific authentication error message to avoid username enumeration.
5. WHEN a customer logs out, THE Store SHALL invalidate the session and redirect to the home page.
6. THE Store SHALL enforce a minimum password length of 8 characters and reject passwords that are entirely numeric during signup.

---

### Requirement 12: Performance and Scalability

**User Story:** As a store owner, I want the platform to perform well under load, so that customers have a fast and reliable shopping experience.

#### Acceptance Criteria

1. THE Store SHALL use `select_related` and `prefetch_related` on all list view queries that access related models (Category, ProductImage, OrderItem) to eliminate N+1 query patterns.
2. WHEN serving the home page, THE Store SHALL execute no more than 5 database queries to render the full page.
3. THE Store SHALL serve all static files (CSS, JS, images) via WhiteNoise with `STATICFILES_STORAGE` set to `CompressedManifestStaticFilesStorage` in production for cache-busting and compression.
4. THE Media_Pipeline SHALL serve product images via Cloudinary CDN with appropriate cache headers in production.
5. THE Store SHALL use Django's database connection pooling (`conn_max_age=600`) in production to reduce connection overhead.

---

### Requirement 13: Error Handling and Resilience

**User Story:** As a customer, I want the application to handle errors gracefully, so that I am never left on a broken page.

#### Acceptance Criteria

1. THE Store SHALL define custom 404 and 500 error page templates that match the site's brand aesthetic.
2. WHEN a requested Product or Category does not exist, THE Store SHALL return a 404 response using the custom error template.
3. IF an unexpected server error occurs, THEN THE Store SHALL return a 500 response using the custom error template and log the error details server-side.
4. WHEN a form submission fails CSRF validation, THE Store SHALL return a 403 response with a user-friendly message.
5. THE Store SHALL validate all URL parameters (e.g., product `pk`, order `id`) and return a 404 response for non-integer or non-existent values.

---

### Requirement 14: Deployment and Infrastructure

**User Story:** As a store owner, I want the application to be reliably deployable to a cloud platform, so that the site is always available to customers.

#### Acceptance Criteria

1. THE Store SHALL include a `Procfile` specifying `gunicorn core.wsgi:application` as the web process for Render/Heroku deployment.
2. THE Store SHALL include a `build.sh` script that runs `collectstatic` and `migrate` as part of the deployment pipeline.
3. THE Store SHALL use `dj-database-url` to parse the `DATABASE_URL` environment variable for production database configuration.
4. THE Store SHALL use `django-environ` to load all environment variables from a `.env` file in local development.
5. THE Store SHALL include a `.dockerignore` and `Dockerfile` supporting containerized deployment with a non-root user and a production-ready gunicorn command.
6. WHEN the application starts in production, THE Store SHALL automatically run pending database migrations as part of the `build.sh` script.
