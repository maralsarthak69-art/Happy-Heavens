# Happy Heavens — Multi-Bug Audit Design

## Overview

This document formalizes the fix approach for 11 bugs identified across three groups in the
Happy Heavens Django e-commerce application. The bugs span security vulnerabilities (open
redirect, CSRF-unsafe logout/cart, missing HSTS flags, startup crash), cart logic errors
(stock overflow, inactive-product count, GET-mutation), and data integrity / UX gaps (missing
email validation, inactive-product slug leak, broken password reset, non-functional newsletter
form). Each fix is targeted and minimal; the design documents the bug condition, expected
behavior, root cause hypothesis, correctness properties, implementation plan, and testing
strategy for every bug.

---

## Glossary

- **Bug_Condition (C)**: The predicate that identifies inputs or states that trigger a specific bug.
- **Property (P)**: The desired correct behavior when the bug condition holds.
- **Preservation**: Existing correct behavior that must remain unchanged after the fix.
- **isBugCondition(input)**: Pseudocode function returning true when the input triggers the bug.
- **expectedBehavior(result)**: Pseudocode function returning true when the result is correct.
- **login_view**: `store/views/auth.py` — handles POST login and `next` redirect.
- **logout_view**: `store/views/auth.py` — handles logout; currently accepts GET.
- **Cart.add**: `store/cart.py` — adds a product quantity to the session cart.
- **Cart.__len__**: `store/cart.py` — returns total item count from session (currently includes inactive).
- **add_to_cart / remove_from_cart**: `store/views/cart.py` — cart mutation views; currently accept GET.
- **product_detail_by_pk**: `store/views/products.py` — PK-based redirect; currently leaks inactive slug.
- **SignUpForm**: `store/forms.py` — user registration form; email field is currently optional.
- **settings.py**: `core/settings.py` — Django settings; missing HSTS flags and ALLOWED_HOST guard.

---

## Bug Details

### Bug 1.1 — Open Redirect on Login

The bug manifests when a user submits the login form with a `next` parameter containing an
external URL. The `login_view` passes `next_url` directly to `redirect()` without validating
whether it is a safe internal path.

**Formal Specification:**
```
FUNCTION isBugCondition_1_1(input)
  INPUT: input of type LoginPOSTRequest
  OUTPUT: boolean

  next_url := input.POST.get('next') OR input.GET.get('next')
  RETURN next_url IS NOT NULL
         AND NOT url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
END FUNCTION
```

**Examples:**
- POST `/login/` with `next=https://evil.com` → redirects to `https://evil.com` (bug)
- POST `/login/` with `next=//evil.com/path` → redirects off-site (bug)
- POST `/login/` with `next=/orders/` → redirects to `/orders/` (correct, not a bug condition)
- POST `/login/` with no `next` → redirects to home (correct, not a bug condition)

---

### Bug 1.2 — CSRF-Unsafe Logout (GET Accepted)

The bug manifests when any GET request is sent to `/logout/`. The `logout_view` calls
`logout(request)` unconditionally regardless of HTTP method, making it exploitable via an
`<img src="/logout/">` tag or a crafted link.

**Formal Specification:**
```
FUNCTION isBugCondition_1_2(input)
  INPUT: input of type HTTPRequest to /logout/
  OUTPUT: boolean

  RETURN input.method == 'GET'
END FUNCTION
```

**Examples:**
- GET `/logout/` → user is logged out without consent (bug)
- `<img src="/logout/">` embedded on any page → silently logs out the user (bug)
- POST `/logout/` with valid CSRF token → correct logout (not a bug condition)

---

### Bug 1.3 — Missing ALLOWED_HOST Crashes at Startup

The bug manifests when `DEBUG=False` and the `ALLOWED_HOST` environment variable is absent.
`env('ALLOWED_HOST')` raises an unhandled `environ.ImproperlyConfigured` (or `KeyError`)
exception with a cryptic message instead of a clear developer-facing error.

**Formal Specification:**
```
FUNCTION isBugCondition_1_3(input)
  INPUT: input of type EnvironmentState at Django startup
  OUTPUT: boolean

  RETURN input.DEBUG == False
         AND 'ALLOWED_HOST' NOT IN input.environment_variables
END FUNCTION
```

**Examples:**
- `DEBUG=False`, `ALLOWED_HOST` missing → startup crash with cryptic error (bug)
- `DEBUG=False`, `ALLOWED_HOST=mysite.com` → starts normally (not a bug condition)
- `DEBUG=True`, `ALLOWED_HOST` missing → `ALLOWED_HOSTS=['*']`, starts normally (not a bug condition)

---

### Bug 1.4 — Missing HSTS Subdomain and Preload Flags

The bug manifests when the application runs in production (`IS_PRODUCTION=True`, `DEBUG=False`)
and `SECURE_HSTS_SECONDS` is set, but `SECURE_HSTS_INCLUDE_SUBDOMAINS` and
`SECURE_HSTS_PRELOAD` are not set, leaving subdomains unprotected.

**Formal Specification:**
```
FUNCTION isBugCondition_1_4(input)
  INPUT: input of type DjangoSettingsState
  OUTPUT: boolean

  RETURN input.DEBUG == False
         AND input.SECURE_HSTS_SECONDS > 0
         AND (input.SECURE_HSTS_INCLUDE_SUBDOMAINS != True
              OR input.SECURE_HSTS_PRELOAD != True)
END FUNCTION
```

**Examples:**
- Production with `SECURE_HSTS_SECONDS=31536000`, flags absent → subdomains unprotected (bug)
- Production with all three HSTS settings present → correct (not a bug condition)
- `DEBUG=True` → HSTS block not entered (not a bug condition)

---

### Bug 1.5 — Cart Quantity Exceeds Stock

The bug manifests when a user adds a product to the cart multiple times. `Cart.add` increments
the quantity without checking whether the new total would exceed `product.stock`.

**Formal Specification:**
```
FUNCTION isBugCondition_1_5(input)
  INPUT: input of type AddToCartRequest {product, current_cart_quantity}
  OUTPUT: boolean

  RETURN input.current_cart_quantity + 1 > input.product.stock
END FUNCTION
```

**Examples:**
- Product with `stock=2`, already 2 in cart, user clicks "Add" → quantity becomes 3 (bug)
- Product with `stock=1`, 0 in cart, user clicks "Add" → quantity becomes 1 (correct)
- Product with `stock=0` → already blocked by existing out-of-stock check (not this bug)

---

### Bug 1.6 — Cart.__len__ Counts Inactive Products

The bug manifests when `Cart.__len__` is called (e.g. for the nav badge). It sums quantities
for all product IDs in the session dict, including IDs of products that have since been
deactivated, inflating the displayed count.

**Formal Specification:**
```
FUNCTION isBugCondition_1_6(input)
  INPUT: input of type CartSessionState
  OUTPUT: boolean

  inactive_ids := {pid for pid in input.cart.keys()
                   WHERE Product.objects.get(id=pid).is_active == False}
  RETURN len(inactive_ids) > 0
END FUNCTION
```

**Examples:**
- Cart has product A (active, qty=2) and product B (inactive, qty=1) → `__len__` returns 3 (bug, should be 2)
- Cart has only active products → `__len__` returns correct count (not a bug condition)

---

### Bug 1.7 — Cart Mutation via GET Request

The bug manifests when a GET request is sent to `/cart/add/<pk>/` or `/cart/remove/<pk>/`.
Both views mutate cart state without checking the HTTP method or requiring a CSRF token.

**Formal Specification:**
```
FUNCTION isBugCondition_1_7(input)
  INPUT: input of type HTTPRequest to /cart/add/<pk>/ or /cart/remove/<pk>/
  OUTPUT: boolean

  RETURN input.method == 'GET'
END FUNCTION
```

**Examples:**
- GET `/cart/add/5/` → product 5 added to cart without user intent (bug)
- `<img src="/cart/remove/3/">` → product 3 silently removed (bug)
- POST `/cart/add/5/` with CSRF token → correct (not a bug condition)

---

### Bug 1.8 — Missing Email Silences Order Notifications

The bug manifests when a user registers without providing an email address. The `SignUpForm`
does not require email, so `instance.user.email` is empty and the `post_save` signal skips
sending order status emails silently.

**Formal Specification:**
```
FUNCTION isBugCondition_1_8(input)
  INPUT: input of type SignupFormData
  OUTPUT: boolean

  RETURN input.email IS NULL OR input.email == ''
END FUNCTION
```

**Examples:**
- Signup with no email → account created, order emails never sent (bug)
- Signup with `email=user@example.com` → order emails sent correctly (not a bug condition)

---

### Bug 1.9 — Inactive Product Slug Leaked via Redirect

The bug manifests when a user visits `/product/<pk>/redirect/` for a product that exists but
has `is_active=False`. `product_detail_by_pk` calls `get_object_or_404(Product, pk=pk)` without
filtering on `is_active`, then issues a 302 redirect to the slug URL, revealing the slug before
the destination returns a 404.

**Formal Specification:**
```
FUNCTION isBugCondition_1_9(input)
  INPUT: input of type HTTPRequest to /product/<pk>/redirect/
  OUTPUT: boolean

  product := Product.objects.get(pk=input.pk)
  RETURN product EXISTS AND product.is_active == False
END FUNCTION
```

**Examples:**
- GET `/product/7/redirect/` where product 7 is inactive → 302 to `/product/hidden-slug/` (bug)
- GET `/product/7/redirect/` where product 7 is active → 302 to slug URL (correct)
- GET `/product/999/redirect/` where product 999 does not exist → 404 (correct)

---

### Bug 1.10 — Broken Password Reset Link

The bug manifests when a user clicks "Forgot Password?" on the login page. The link points to
`#` (a no-op anchor) because no password reset URL or view is wired up.

**Formal Specification:**
```
FUNCTION isBugCondition_1_10(input)
  INPUT: input of type LoginPageState
  OUTPUT: boolean

  forgot_password_href := parse_login_template_forgot_password_link()
  RETURN forgot_password_href == '#'
         OR forgot_password_href does not resolve to a valid URL pattern
END FUNCTION
```

**Examples:**
- User clicks "Forgot Password?" → stays on `#`, no reset flow initiated (bug)
- After fix: user clicks link → navigates to password reset form (correct)

---

### Bug 1.11 — Non-functional Newsletter Form

The bug manifests when a user fills in the newsletter input in the footer and presses Enter or
clicks a submit button. The input has no surrounding `<form>` element, no `action` URL, and no
backend handler, so the submission is silently lost.

**Formal Specification:**
```
FUNCTION isBugCondition_1_11(input)
  INPUT: input of type FooterNewsletterSubmission
  OUTPUT: boolean

  RETURN newsletter_input_has_no_form_element()
         OR newsletter_form_has_no_action_url()
         OR no_backend_handler_exists_for_newsletter()
END FUNCTION
```

**Examples:**
- User types email in footer input and presses Enter → nothing happens (bug)
- After fix (backend handler): submission is processed and user sees confirmation (correct)
- After fix (remove input): input is absent, no misleading UI element (correct)

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- 3.1 A valid internal `next` URL on login continues to redirect the user to that internal path after authentication
- 3.2 A POST logout with a valid CSRF token continues to log the user out and redirect to home
- 3.3 Adding a product to the cart where quantity does not exceed stock continues to work correctly
- 3.4 `Cart.__iter__` continues to filter out inactive products, remove them from the session, and populate `self.removed_items`
- 3.5 Active product detail pages continue to display correctly
- 3.6 Checkout continues to atomically decrement stock, create Order/OrderItems, clear the cart, and redirect to success
- 3.7 Order status change emails continue to be sent when the customer has an email address on file
- 3.8 Custom request form submission continues to save the request and notify the store owner
- 3.9 Product search continues to return paginated results across active products only
- 3.10 Order history continues to show only the authenticated user's own orders, paginated at 10 per page

**Scope:**
All inputs that do NOT satisfy any of the 11 bug conditions above must be completely unaffected
by the fixes. This includes normal authenticated flows, valid cart operations within stock
limits, active product browsing, and all admin operations.

---

## Hypothesized Root Cause

**Bug 1.1 — Open Redirect:**
`login_view` passes `next_url` directly to `redirect()` without calling
`url_has_allowed_host_and_scheme`. Django provides this utility in
`django.utils.http` but it is not used here.

**Bug 1.2 — CSRF-Unsafe Logout:**
`logout_view` has no `if request.method == 'POST'` guard and no `@require_POST` decorator.
Django's own `LogoutView` requires POST since Django 5.0; this custom view was not updated.

**Bug 1.3 — Startup Crash on Missing ALLOWED_HOST:**
`env('ALLOWED_HOST')` in the `else` branch of the `DEBUG` check raises an unhandled exception
when the variable is absent. No `try/except` or `env('ALLOWED_HOST', default=None)` guard
with a descriptive `ImproperlyConfigured` raise is present.

**Bug 1.4 — Missing HSTS Flags:**
The production security block in `settings.py` sets `SECURE_HSTS_SECONDS` but omits
`SECURE_HSTS_INCLUDE_SUBDOMAINS` and `SECURE_HSTS_PRELOAD`. These were likely overlooked
when the HSTS setting was first added.

**Bug 1.5 — Cart Quantity Exceeds Stock:**
`Cart.add` increments `quantity` unconditionally. The `add_to_cart` view only checks
`product.stock == 0` (out-of-stock), not whether the new cumulative quantity would exceed
`product.stock`. The stock-cap check is missing entirely.

**Bug 1.6 — Cart.__len__ Counts Inactive Products:**
`Cart.__len__` sums over `self.cart.values()` which is the raw session dict. It does not
query the database to filter out inactive product IDs, unlike `Cart.__iter__` and
`Cart.get_total_price` which do filter on `is_active=True`.

**Bug 1.7 — Cart Mutation via GET:**
`add_to_cart` and `remove_from_cart` have no `@require_POST` decorator and no method check.
The views were written without CSRF-method enforcement, likely because they were initially
simple redirect helpers.

**Bug 1.8 — Missing Email Silences Notifications:**
`SignUpForm` inherits from `UserCreationForm` and lists `email` in `fields`, but Django's
`User.email` is optional by default. No `required=True` or custom validator was added to
the form field, so the field is submitted empty without error.

**Bug 1.9 — Inactive Product Slug Leaked:**
`product_detail_by_pk` calls `get_object_or_404(Product, pk=pk)` without `is_active=True`.
The intent was a legacy redirect helper, but it does not apply the same active-product filter
used by `product_detail`.

**Bug 1.10 — Broken Password Reset Link:**
The login template hardcodes `href="#"` for the "Forgot Password?" link. Django's built-in
`django.contrib.auth` password reset URLs were never added to `core/urls.py` and the template
was never updated to reference them.

**Bug 1.11 — Non-functional Newsletter Form:**
The newsletter input in the footer template is a bare `<input>` element with no enclosing
`<form>`, no `action`, and no corresponding URL or view. It was added as a UI placeholder
and never wired up to a backend.

---

## Correctness Properties

Property 1: Bug Condition — Open Redirect Blocked

_For any_ login POST request where `next` is an external or unsafe URL
(isBugCondition_1_1 returns true), the fixed `login_view` SHALL redirect the authenticated
user to the home page instead of the external URL.

**Validates: Requirements 2.1**

---

Property 2: Preservation — Valid Internal Next Redirect

_For any_ login POST request where `next` is a safe internal path
(isBugCondition_1_1 returns false and `next` is non-empty), the fixed `login_view` SHALL
continue to redirect the user to that internal path after successful authentication.

**Validates: Requirements 3.1**

---

Property 3: Bug Condition — GET Logout Rejected

_For any_ GET request to `/logout/` (isBugCondition_1_2 returns true), the fixed
`logout_view` SHALL NOT log the user out and SHALL return a 405 Method Not Allowed response.

**Validates: Requirements 2.2**

---

Property 4: Preservation — POST Logout Still Works

_For any_ POST request to `/logout/` with a valid CSRF token
(isBugCondition_1_2 returns false), the fixed `logout_view` SHALL continue to log the user
out and redirect to the home page.

**Validates: Requirements 3.2**

---

Property 5: Bug Condition — Descriptive Startup Error for Missing ALLOWED_HOST

_For any_ startup environment where `DEBUG=False` and `ALLOWED_HOST` is absent
(isBugCondition_1_3 returns true), the fixed settings SHALL raise an `ImproperlyConfigured`
exception with a message that names the missing `ALLOWED_HOST` variable.

**Validates: Requirements 2.3**

---

Property 6: Bug Condition — HSTS Subdomain and Preload Flags Present

_For any_ production settings state where `SECURE_HSTS_SECONDS > 0`
(isBugCondition_1_4 returns true), the fixed settings SHALL also set
`SECURE_HSTS_INCLUDE_SUBDOMAINS = True` and `SECURE_HSTS_PRELOAD = True`.

**Validates: Requirements 2.4**

---

Property 7: Bug Condition — Cart Quantity Capped at Stock

_For any_ add-to-cart request where the resulting quantity would exceed `product.stock`
(isBugCondition_1_5 returns true), the fixed `add_to_cart` view SHALL reject the addition,
leave the cart quantity unchanged, and display an error message indicating the maximum
available quantity.

**Validates: Requirements 2.5**

---

Property 8: Preservation — Valid Cart Additions Still Work

_For any_ add-to-cart request where the resulting quantity does not exceed `product.stock`
(isBugCondition_1_5 returns false), the fixed `add_to_cart` view SHALL continue to increment
the cart quantity correctly.

**Validates: Requirements 3.3**

---

Property 9: Bug Condition — Cart.__len__ Excludes Inactive Products

_For any_ cart session state containing at least one inactive product ID
(isBugCondition_1_6 returns true), the fixed `Cart.__len__` SHALL return only the sum of
quantities for active products, matching the count visible to the user in the cart.

**Validates: Requirements 2.6**

---

Property 10: Preservation — Cart.__iter__ Behavior Unchanged

_For any_ cart session state (isBugCondition_1_6 may or may not hold), the fixed
`Cart.__iter__` SHALL continue to filter out inactive products, remove them from the session,
and populate `self.removed_items` exactly as before.

**Validates: Requirements 3.4**

---

Property 11: Bug Condition — GET Cart Mutation Rejected

_For any_ GET request to `/cart/add/<pk>/` or `/cart/remove/<pk>/`
(isBugCondition_1_7 returns true), the fixed views SHALL NOT mutate the cart and SHALL
return a 405 Method Not Allowed response.

**Validates: Requirements 2.7**

---

Property 12: Bug Condition — Email Required on Signup

_For any_ signup form submission where the email field is empty or absent
(isBugCondition_1_8 returns true), the fixed `SignUpForm` SHALL reject the submission with
a validation error requiring a valid email address.

**Validates: Requirements 2.8**

---

Property 13: Bug Condition — Inactive Product Redirect Returns 404

_For any_ request to `/product/<pk>/redirect/` where the product exists but is inactive
(isBugCondition_1_9 returns true), the fixed `product_detail_by_pk` SHALL return a 404
response without issuing a redirect or revealing the product's slug.

**Validates: Requirements 2.9**

---

Property 14: Preservation — Active Product Redirect Still Works

_For any_ request to `/product/<pk>/redirect/` where the product is active
(isBugCondition_1_9 returns false), the fixed view SHALL continue to redirect to the
correct slug URL.

**Validates: Requirements 3.5**

---

Property 15: Bug Condition — Password Reset Link Is Functional

_For any_ login page render (isBugCondition_1_10 returns true on unfixed code), the fixed
template SHALL render the "Forgot Password?" link pointing to a valid, resolvable URL that
leads to a functional password reset flow.

**Validates: Requirements 2.10**

---

Property 16: Bug Condition — Newsletter Form Is Functional or Removed

_For any_ footer render (isBugCondition_1_11 returns true on unfixed code), the fixed
template SHALL either (a) wrap the newsletter input in a `<form>` with a valid `action` URL
backed by a handler that processes the subscription, or (b) remove the input entirely so no
misleading UI element is shown.

**Validates: Requirements 2.11**

---

## Fix Implementation

### Bug 1.1 — Open Redirect on Login

**File:** `store/views/auth.py`
**Function:** `login_view`

**Changes Required:**
1. Import `url_has_allowed_host_and_scheme` from `django.utils.http`.
2. After authenticating the user, validate `next_url` using
   `url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})`.
3. If the URL is not safe, fall back to `'home'`.

---

### Bug 1.2 — CSRF-Unsafe Logout

**File:** `store/views/auth.py`
**Function:** `logout_view`

**Changes Required:**
1. Add `@require_POST` decorator (import from `django.views.decorators.http`).
2. The CSRF middleware already enforces token validation on POST requests — no additional
   change needed beyond requiring POST.
3. Update any logout links in templates to use a `<form method="post">` with `{% csrf_token %}`.

---

### Bug 1.3 — Missing ALLOWED_HOST Startup Crash

**File:** `core/settings.py`

**Changes Required:**
1. Wrap the `env('ALLOWED_HOST')` call in a `try/except` or use
   `env('ALLOWED_HOST', default=None)`.
2. If the value is `None` (or empty), raise
   `django.core.exceptions.ImproperlyConfigured` with a message such as:
   `"ALLOWED_HOST environment variable is required when DEBUG=False."`.

---

### Bug 1.4 — Missing HSTS Flags

**File:** `core/settings.py`

**Changes Required:**
1. In the `if not DEBUG:` security block, add:
   - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
   - `SECURE_HSTS_PRELOAD = True`
   immediately after the existing `SECURE_HSTS_SECONDS` line.

---

### Bug 1.5 — Cart Quantity Exceeds Stock

**File:** `store/views/cart.py`
**Function:** `add_to_cart`

**Changes Required:**
1. After fetching the product, read the current cart quantity for that product.
2. If `current_quantity + 1 > product.stock`, add an error message and redirect without
   calling `cart.add`.
3. The `Cart.add` method itself may optionally accept a `max_quantity` guard, but the
   primary enforcement belongs in the view.

---

### Bug 1.6 — Cart.__len__ Counts Inactive Products

**File:** `store/cart.py`
**Function:** `Cart.__len__`

**Changes Required:**
1. Query the database for active product IDs among the keys in `self.cart`:
   ```python
   active_ids = set(
       str(pk) for pk in Product.objects.filter(
           id__in=self.cart.keys(), is_active=True
       ).values_list('id', flat=True)
   )
   ```
2. Sum quantities only for items whose ID is in `active_ids`.

---

### Bug 1.7 — Cart Mutation via GET

**File:** `store/views/cart.py`
**Functions:** `add_to_cart`, `remove_from_cart`

**Changes Required:**
1. Add `@require_POST` decorator to both `add_to_cart` and `remove_from_cart`.
2. Update any template links that use `<a href="...">` for add/remove to use
   `<form method="post">` with `{% csrf_token %}` instead.

---

### Bug 1.8 — Missing Email on Signup

**File:** `store/forms.py`
**Class:** `SignUpForm`

**Changes Required:**
1. In `SignUpForm.__init__` (or via field declaration), set `self.fields['email'].required = True`.
2. Optionally add an `EmailValidator` or use `forms.EmailField` override to enforce format.

---

### Bug 1.9 — Inactive Product Slug Leaked

**File:** `store/views/products.py`
**Function:** `product_detail_by_pk`

**Changes Required:**
1. Change `get_object_or_404(Product, pk=pk)` to
   `get_object_or_404(Product, pk=pk, is_active=True)`.
2. This causes inactive products to return a 404 without revealing the slug.

---

### Bug 1.10 — Broken Password Reset Link

**Files:** `core/urls.py`, login template

**Changes Required:**
1. In `core/urls.py`, include Django's built-in auth URLs:
   ```python
   path('accounts/', include('django.contrib.auth.urls')),
   ```
2. In the login template, replace `href="#"` with `href="{% url 'password_reset' %}"`.
3. Optionally create custom password reset templates under `templates/registration/` to
   match the site's design.

---

### Bug 1.11 — Non-functional Newsletter Form

**Chosen approach:** Implement a minimal backend handler (preferred over silent removal).

**Files:** footer template, `store/urls.py`, `store/views/` (new view), `store/models.py` (optional)

**Changes Required:**
1. Create a `newsletter_subscribe` view that accepts POST, validates the email, saves or
   processes the subscription, and returns a JSON response or redirect with a success message.
2. Add a URL pattern: `path('newsletter/subscribe/', newsletter_subscribe, name='newsletter_subscribe')`.
3. Wrap the footer input in a `<form method="post" action="{% url 'newsletter_subscribe' %}">` with `{% csrf_token %}`.

*Alternative:* If a newsletter backend is out of scope, remove the input from the template
entirely to eliminate the misleading UI element.

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach for each bug: first, write exploratory tests
that run against the UNFIXED code to surface counterexamples and confirm the root cause; then,
after the fix, run fix-checking and preservation-checking tests to verify correctness and
prevent regressions.

---

### Exploratory Bug Condition Checking

**Goal:** Surface counterexamples that demonstrate each bug on unfixed code. Confirm or refute
the root cause hypotheses. If a hypothesis is refuted, re-hypothesize before implementing.

**Test Cases (run on UNFIXED code):**

1. **Open Redirect Test (1.1):** POST to `/login/` with valid credentials and
   `next=https://evil.com`. Assert the response redirects to `https://evil.com`. Expected to
   pass on unfixed code (demonstrating the bug).

2. **GET Logout Test (1.2):** Send GET to `/logout/` while authenticated. Assert the user
   session is destroyed. Expected to pass on unfixed code (demonstrating the bug).

3. **Missing ALLOWED_HOST Test (1.3):** Temporarily unset `ALLOWED_HOST` with `DEBUG=False`
   and attempt to load settings. Assert a cryptic/unhandled exception is raised (not a clear
   `ImproperlyConfigured` message).

4. **Missing HSTS Flags Test (1.4):** With `DEBUG=False`, assert
   `settings.SECURE_HSTS_INCLUDE_SUBDOMAINS` and `settings.SECURE_HSTS_PRELOAD` are not set
   (or are `False`/absent).

5. **Stock Overflow Test (1.5):** Add a product with `stock=1` to the cart twice. Assert
   `cart[product_id]['quantity'] == 2` on unfixed code (demonstrating the bug).

6. **Inactive Count Test (1.6):** Add an active product (qty=2) and an inactive product (qty=1)
   to the session. Assert `len(cart) == 3` on unfixed code (demonstrating the bug).

7. **GET Cart Mutation Test (1.7):** Send GET to `/cart/add/<pk>/`. Assert the product is
   added to the cart on unfixed code (demonstrating the bug).

8. **Empty Email Signup Test (1.8):** Submit `SignUpForm` with `email=''`. Assert the form
   is valid and the user is created on unfixed code (demonstrating the bug).

9. **Inactive Product Redirect Test (1.9):** Request `/product/<pk>/redirect/` for an inactive
   product. Assert the response is a 302 redirect (not 404) on unfixed code.

10. **Forgot Password Link Test (1.10):** Parse the login template and assert the "Forgot
    Password?" href is `#` on unfixed code.

11. **Newsletter Form Test (1.11):** Parse the footer template and assert the newsletter input
    has no enclosing `<form>` element on unfixed code.

**Expected Counterexamples:**
- Bugs 1.1, 1.2, 1.5, 1.6, 1.7, 1.8, 1.9 will produce observable incorrect behavior in
  HTTP responses or session state.
- Bugs 1.3, 1.4, 1.10, 1.11 will produce incorrect configuration or template state.

---

### Fix Checking

**Goal:** Verify that for all inputs where each bug condition holds, the fixed code produces
the expected behavior.

**Pseudocode (generic):**
```
FOR ALL input WHERE isBugCondition_N(input) DO
  result := fixedFunction(input)
  ASSERT expectedBehavior_N(result)
END FOR
```

**Per-bug fix checks:**
- 1.1: External `next` → response redirects to home, not the external URL.
- 1.2: GET `/logout/` → response is 405, user session intact.
- 1.3: Missing `ALLOWED_HOST` with `DEBUG=False` → `ImproperlyConfigured` with descriptive message.
- 1.4: Production settings → `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`, `SECURE_HSTS_PRELOAD=True`.
- 1.5: Add beyond stock → 400/redirect with error message, cart quantity unchanged.
- 1.6: Cart with inactive product → `len(cart)` equals only active product quantities.
- 1.7: GET `/cart/add/<pk>/` → 405, cart unchanged.
- 1.8: Signup with empty email → form validation error on email field.
- 1.9: Inactive product PK redirect → 404 response.
- 1.10: Login template "Forgot Password?" href → resolves to `password_reset` URL.
- 1.11: Footer newsletter → form element present with valid action, or input absent.

---

### Preservation Checking

**Goal:** Verify that for all inputs where the bug condition does NOT hold, the fixed code
produces the same result as the original code.

**Pseudocode (generic):**
```
FOR ALL input WHERE NOT isBugCondition_N(input) DO
  ASSERT originalFunction(input) = fixedFunction(input)
END FOR
```

**Testing Approach:** Property-based testing is recommended for bugs 1.1, 1.5, 1.6 because
they involve a range of inputs (many possible `next` URLs, many stock/quantity combinations,
many cart compositions). Unit tests are sufficient for the remaining bugs.

**Preservation test cases:**
- 1.1: Internal `next` URLs → still redirect to the internal path after login.
- 1.2: POST logout with CSRF → still logs out and redirects to home.
- 1.3: `ALLOWED_HOST` present with `DEBUG=False` → settings load normally.
- 1.4: `DEBUG=True` → HSTS block not entered, no change to dev behavior.
- 1.5: Add within stock limit → cart quantity increments correctly.
- 1.6: Cart with only active products → `__len__` returns same value as before.
- 1.7: POST cart add/remove with CSRF → cart mutates correctly.
- 1.8: Signup with valid email → account created, email stored.
- 1.9: Active product PK redirect → still redirects to slug URL.
- 1.10: Other login page elements → unaffected by template change.
- 1.11: Other footer elements → unaffected by newsletter form change.

---

### Unit Tests

- Test `login_view` with external `next` → redirects to home.
- Test `login_view` with internal `next` → redirects to internal path.
- Test `logout_view` GET → 405, session intact.
- Test `logout_view` POST → 200/redirect, session cleared.
- Test settings with missing `ALLOWED_HOST` and `DEBUG=False` → `ImproperlyConfigured`.
- Test production settings → HSTS flags present.
- Test `add_to_cart` when quantity would exceed stock → error message, cart unchanged.
- Test `add_to_cart` within stock → cart incremented.
- Test `Cart.__len__` with mixed active/inactive session → returns only active count.
- Test `Cart.__iter__` with inactive product → removes from session, populates `removed_items`.
- Test GET `/cart/add/<pk>/` → 405.
- Test GET `/cart/remove/<pk>/` → 405.
- Test `SignUpForm` with empty email → validation error.
- Test `SignUpForm` with valid email → form valid.
- Test `product_detail_by_pk` with inactive product → 404.
- Test `product_detail_by_pk` with active product → 302 to slug.
- Test login template "Forgot Password?" href resolves to a valid URL.
- Test newsletter form element presence (or absence) in footer template.

---

### Property-Based Tests

- **Property 1 (Open Redirect):** Generate arbitrary URL strings as `next` values. For any
  URL that is not a safe internal path, assert the fixed `login_view` redirects to home.
  For any safe internal path, assert it redirects to that path.

- **Property 7 (Stock Cap):** Generate random `(stock, add_count)` pairs where
  `add_count > stock`. Assert the cart quantity never exceeds `stock` after any sequence of
  add operations.

- **Property 8 (Valid Cart Additions):** Generate random `(stock, add_count)` pairs where
  `add_count <= stock`. Assert the cart quantity equals `add_count` after the operations.

- **Property 9 (Cart.__len__ Active Only):** Generate random cart sessions with arbitrary
  mixes of active and inactive product IDs and quantities. Assert `len(cart)` equals the sum
  of quantities for active products only.

---

### Integration Tests

- Full login flow with external `next` → ends at home page, not external site.
- Full login flow with internal `next` → ends at the correct internal page.
- Full logout flow via POST form → user is logged out, redirected to home.
- Full checkout flow with valid cart → stock decremented, order created, cart cleared.
- Full signup with email → order status email sent on status change.
- Full signup without email (after fix) → form rejected with validation error.
- Browse inactive product by PK → 404, no slug revealed.
- Browse active product by PK → redirected to product detail page.
- Password reset flow end-to-end → user receives reset email and can set new password.
- Newsletter subscription (if implemented) → submission processed, confirmation shown.
