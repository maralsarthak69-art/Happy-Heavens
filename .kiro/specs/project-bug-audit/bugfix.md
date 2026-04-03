# Bugfix Requirements Document

## Introduction

A comprehensive audit of the Happy Heavens Django e-commerce application revealed multiple bugs spanning security vulnerabilities, logic errors, and missing functionality. The issues range from a critical open redirect in the login flow and CSRF-unsafe logout, to cart quantity logic that allows stock to be exceeded, and several UX/data integrity gaps. This document captures all identified defects, their expected correct behavior, and the existing behavior that must be preserved.

---

## Bug Analysis

### Current Behavior (Defect)

**Bug Group A — Security**

1.1 WHEN a user submits the login form with a `next` parameter pointing to an external URL (e.g. `next=https://evil.com`) THEN the system redirects the authenticated user to that external URL without validation

1.2 WHEN any browser or script sends a GET request to `/logout/` THEN the system logs the user out without requiring a POST request or CSRF token, making the logout endpoint exploitable via a simple image tag or link

1.3 WHEN `DEBUG=False` is set in production and the `ALLOWED_HOST` environment variable is missing THEN the system crashes at startup with an unhandled `ImproperlyConfigured` exception instead of a clear error message

1.4 WHEN the application is running in production (`IS_PRODUCTION=True`) and `SECURE_HSTS_SECONDS` is set THEN the system does not set `SECURE_HSTS_INCLUDE_SUBDOMAINS` or `SECURE_HSTS_PRELOAD`, leaving subdomains unprotected by HSTS

**Bug Group B — Cart Logic**

1.5 WHEN a user clicks "Add to Cart" on a product that has `stock > 0` multiple times THEN the system increments the cart quantity each time without checking whether the accumulated quantity exceeds available stock, allowing the cart to hold more units than exist

1.6 WHEN `Cart.__len__` is called (e.g. for the nav badge count) THEN the system counts all product IDs in the session including deactivated products, causing the cart badge to display an inflated count that does not match what the user actually sees in the cart

1.7 WHEN a GET request is made to `/cart/add/<pk>/` or `/cart/remove/<pk>/` THEN the system mutates the cart without requiring a POST request or CSRF token, making cart state modifiable by any external link or embedded resource

**Bug Group C — Data Integrity / UX**

1.8 WHEN a user registers via the signup form without providing an email address THEN the system creates the account successfully, but order status notification emails are silently skipped for that user because the signal checks `if customer_email` and finds it empty

1.9 WHEN a user visits `/product/<int:pk>/redirect/` for a product that exists but has `is_active=False` THEN the system reveals the product's slug in the redirect response (HTTP 302) before the destination URL returns a 404, leaking the existence and slug of inactive products

1.10 WHEN a user clicks the "Forgot Password?" link on the login page THEN the system navigates to `#` (a no-op anchor) because no password reset flow is implemented or linked

1.11 WHEN a user submits the newsletter subscription form in the footer THEN the system does nothing because the input has no surrounding `<form>` element, no action URL, and no backend handler — the submission is silently lost

---

### Expected Behavior (Correct)

**Bug Group A — Security**

2.1 WHEN a user submits the login form with a `next` parameter THEN the system SHALL validate that the `next` URL is a safe internal path (using `url_has_allowed_host_and_scheme`) and redirect to it only if safe, otherwise redirect to the home page

2.2 WHEN a request is made to `/logout/` THEN the system SHALL only process the logout if the request method is POST and a valid CSRF token is present; GET requests SHALL be ignored or redirected

2.3 WHEN `DEBUG=False` and the `ALLOWED_HOST` environment variable is missing THEN the system SHALL raise a clear, descriptive `ImproperlyConfigured` error at startup that names the missing variable

2.4 WHEN `SECURE_HSTS_SECONDS` is configured in production THEN the system SHALL also set `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` and `SECURE_HSTS_PRELOAD = True`

**Bug Group B — Cart Logic**

2.5 WHEN a user attempts to add a product to the cart and the resulting cart quantity would exceed `product.stock` THEN the system SHALL reject the addition and display an error message indicating the maximum available quantity

2.6 WHEN `Cart.__len__` is called THEN the system SHALL return only the count of items whose product IDs correspond to active (`is_active=True`) products in the database

2.7 WHEN a request is made to `/cart/add/<pk>/` or `/cart/remove/<pk>/` THEN the system SHALL only process the mutation if the request method is POST, returning a 405 Method Not Allowed for GET requests

**Bug Group C — Data Integrity / UX**

2.8 WHEN a user registers via the signup form THEN the system SHALL require a valid, non-empty email address so that order notification emails can be delivered

2.9 WHEN a user visits `/product/<int:pk>/redirect/` for a product that has `is_active=False` THEN the system SHALL return a 404 response without revealing the product's slug or existence

2.10 WHEN a user clicks the "Forgot Password?" link on the login page THEN the system SHALL navigate to a functional password reset page (Django's built-in `password_reset` view or a custom equivalent)

2.11 WHEN a user submits the newsletter subscription form in the footer THEN the system SHALL either process the subscription via a proper form with a backend handler, or the non-functional input SHALL be removed from the UI to avoid misleading users

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user logs in with a valid `next` parameter pointing to an internal URL THEN the system SHALL CONTINUE TO redirect the user to that internal URL after successful authentication

3.2 WHEN a logged-in user clicks the logout button (via a POST form) THEN the system SHALL CONTINUE TO log the user out and redirect to the home page

3.3 WHEN a user adds a product to the cart where the quantity does not exceed available stock THEN the system SHALL CONTINUE TO add the product and increment the cart quantity correctly

3.4 WHEN `Cart.__iter__` is called THEN the system SHALL CONTINUE TO filter out inactive products, remove them from the session, and populate `self.removed_items` for display

3.5 WHEN a user visits a product detail page for an active product THEN the system SHALL CONTINUE TO display the product correctly with its images, price, and stock status

3.6 WHEN a user completes checkout with valid cart items and sufficient stock THEN the system SHALL CONTINUE TO atomically decrement stock, create the Order and OrderItems, clear the cart, and redirect to the order success page

3.7 WHEN an admin updates an order's status THEN the system SHALL CONTINUE TO trigger the `post_save` signal and send a status-change email to the customer if they have an email address on file

3.8 WHEN a user submits the custom request form with valid data THEN the system SHALL CONTINUE TO save the request and notify the store owner via email

3.9 WHEN a user searches for products THEN the system SHALL CONTINUE TO return paginated results filtered by name, description, and category across active products only

3.10 WHEN a user views their order history THEN the system SHALL CONTINUE TO show only their own orders, paginated at 10 per page
