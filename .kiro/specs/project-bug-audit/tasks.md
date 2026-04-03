# Implementation Plan

---

## Group A — Security (Bugs 1.1–1.4)

- [x] 1. Write bug condition exploration tests — Group A Security
  - **Property 1: Bug Condition** - Security Bugs (Open Redirect, GET Logout, Missing ALLOWED_HOST, Missing HSTS Flags)
  - **CRITICAL**: These tests MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **GOAL**: Surface counterexamples that demonstrate each security bug exists
  - **Bug 1.1 — Open Redirect:** POST to `/login/` with valid credentials and `next=https://evil.com`; assert response redirects to `https://evil.com` (isBugCondition_1_1: next_url is external and not safe)
  - **Bug 1.2 — GET Logout:** Send GET to `/logout/` while authenticated; assert user session is destroyed (isBugCondition_1_2: request.method == 'GET')
  - **Bug 1.3 — Missing ALLOWED_HOST:** With `DEBUG=False` and `ALLOWED_HOST` unset, attempt to load settings; assert a cryptic/unhandled exception is raised rather than a clear `ImproperlyConfigured` message (isBugCondition_1_3: DEBUG=False AND 'ALLOWED_HOST' not in env)
  - **Bug 1.4 — Missing HSTS Flags:** With `DEBUG=False`, assert `settings.SECURE_HSTS_INCLUDE_SUBDOMAINS` and `settings.SECURE_HSTS_PRELOAD` are absent or False (isBugCondition_1_4: SECURE_HSTS_SECONDS > 0 AND flags missing)
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found to understand root causes
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Write preservation property tests — Group A Security (BEFORE implementing fixes)
  - **Property 2: Preservation** - Valid Internal Redirect, POST Logout, Normal Startup, Dev Settings
  - **IMPORTANT**: Follow observation-first methodology — observe behavior on UNFIXED code for non-buggy inputs
  - **Bug 1.1 preservation:** POST login with `next=/orders/` → observe redirect to `/orders/`; write test asserting internal `next` URLs continue to redirect correctly (isBugCondition_1_1 returns false)
  - **Bug 1.2 preservation:** POST `/logout/` with valid CSRF token → observe logout + redirect to home; write test asserting POST logout still works (isBugCondition_1_2 returns false)
  - **Bug 1.3 preservation:** With `DEBUG=False` and `ALLOWED_HOST=mysite.com` present → observe normal startup; write test asserting settings load without error
  - **Bug 1.4 preservation:** With `DEBUG=True` → observe HSTS block not entered; write test asserting dev settings are unaffected
  - Verify all preservation tests PASS on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2_

- [x] 3. Fix Group A — Security bugs

  - [x] 3.1 Fix Bug 1.1 — Open Redirect on Login
    - File: `store/views/auth.py`, function `login_view`
    - Import `url_has_allowed_host_and_scheme` from `django.utils.http`
    - After authenticating, validate `next_url` with `url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})`
    - If URL is not safe, fall back to `'home'`
    - _Bug_Condition: isBugCondition_1_1(input) where next_url is external/unsafe_
    - _Expected_Behavior: redirect to home when next is unsafe; redirect to next when safe internal path_
    - _Preservation: valid internal next URLs must continue to redirect correctly (3.1)_
    - _Requirements: 2.1, 3.1_

  - [x] 3.2 Fix Bug 1.2 — CSRF-Unsafe Logout
    - File: `store/views/auth.py`, function `logout_view`
    - Add `@require_POST` decorator (import from `django.views.decorators.http`)
    - Update any logout `<a href>` links in templates to use `<form method="post">` with `{% csrf_token %}`
    - _Bug_Condition: isBugCondition_1_2(input) where input.method == 'GET'_
    - _Expected_Behavior: GET /logout/ returns 405; POST with CSRF token logs out and redirects to home_
    - _Preservation: POST logout with valid CSRF token must continue to work (3.2)_
    - _Requirements: 2.2, 3.2_

  - [x] 3.3 Fix Bug 1.3 — Missing ALLOWED_HOST Startup Crash
    - File: `core/settings.py`
    - Use `env('ALLOWED_HOST', default=None)` instead of bare `env('ALLOWED_HOST')`
    - If value is None/empty, raise `django.core.exceptions.ImproperlyConfigured` with message: `"ALLOWED_HOST environment variable is required when DEBUG=False."`
    - _Bug_Condition: isBugCondition_1_3(input) where DEBUG=False AND 'ALLOWED_HOST' not in env_
    - _Expected_Behavior: raises ImproperlyConfigured with descriptive message naming the missing variable_
    - _Preservation: when ALLOWED_HOST is present, settings load normally_
    - _Requirements: 2.3_

  - [x] 3.4 Fix Bug 1.4 — Missing HSTS Subdomain and Preload Flags
    - File: `core/settings.py`
    - In the `if not DEBUG:` security block, add `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` and `SECURE_HSTS_PRELOAD = True` immediately after `SECURE_HSTS_SECONDS`
    - _Bug_Condition: isBugCondition_1_4(input) where SECURE_HSTS_SECONDS > 0 AND flags absent_
    - _Expected_Behavior: SECURE_HSTS_INCLUDE_SUBDOMAINS=True and SECURE_HSTS_PRELOAD=True are set in production_
    - _Preservation: DEBUG=True path is unaffected_
    - _Requirements: 2.4_

  - [x] 3.5 Verify bug condition exploration tests now pass (Group A)
    - **Property 1: Expected Behavior** - Security Bugs Fixed
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - Run all four bug condition tests from task 1 on FIXED code
    - **EXPECTED OUTCOME**: All four tests PASS (confirms bugs 1.1–1.4 are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.6 Verify preservation tests still pass (Group A)
    - **Property 2: Preservation** - Security Preservation
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in login/logout/startup/dev flows)

- [x] 4. Checkpoint — Group A all tests pass
  - Ensure all Group A exploration and preservation tests pass; ask the user if questions arise

---

## Group B — Cart Logic (Bugs 1.5–1.7)

- [x] 5. Write bug condition exploration tests — Group B Cart Logic
  - **Property 1: Bug Condition** - Cart Logic Bugs (Stock Overflow, Inactive Count, GET Mutation)
  - **CRITICAL**: These tests MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **GOAL**: Surface counterexamples that demonstrate each cart logic bug exists
  - **Bug 1.5 — Stock Overflow:** Add a product with `stock=1` to the cart twice; assert `cart[product_id]['quantity'] == 2` on unfixed code (isBugCondition_1_5: current_qty + 1 > product.stock)
  - **Bug 1.6 — Inactive Count:** Build a cart session with active product (qty=2) and inactive product (qty=1); assert `len(cart) == 3` on unfixed code (isBugCondition_1_6: inactive product IDs present in session)
  - **Bug 1.7 — GET Cart Mutation:** Send GET to `/cart/add/<pk>/`; assert the product is added to the cart on unfixed code (isBugCondition_1_7: request.method == 'GET')
  - **Scoped PBT for 1.5:** Scope property to concrete case: stock=1, add twice → quantity=2 (exceeds stock)
  - **Scoped PBT for 1.6:** Scope property to concrete case: one active + one inactive product in session
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.5, 1.6, 1.7_

- [x] 6. Write preservation property tests — Group B Cart Logic (BEFORE implementing fixes)
  - **Property 2: Preservation** - Valid Cart Operations, Cart.__iter__ Behavior, POST Cart Mutation
  - **IMPORTANT**: Follow observation-first methodology
  - **Bug 1.5 preservation:** Add product with `stock=3` once → observe qty=1; write property-based test: for all (stock, add_count) where add_count <= stock, cart quantity equals add_count after operations (isBugCondition_1_5 returns false)
  - **Bug 1.6 preservation:** Cart with only active products → observe `len(cart)` equals sum of quantities; write property-based test asserting this holds for all-active carts (isBugCondition_1_6 returns false)
  - **Bug 1.6 iter preservation:** Call `Cart.__iter__` with inactive product in session → observe inactive product removed and added to `removed_items`; write test asserting `__iter__` behavior is unchanged (Requirement 3.4)
  - **Bug 1.7 preservation:** POST `/cart/add/<pk>/` with CSRF token → observe cart mutates correctly; write test asserting POST add/remove still works
  - Verify all preservation tests PASS on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.3, 3.4_

- [x] 7. Fix Group B — Cart Logic bugs

  - [x] 7.1 Fix Bug 1.5 — Cart Quantity Exceeds Stock
    - File: `store/views/cart.py`, function `add_to_cart`
    - After fetching the product, read current cart quantity for that product
    - If `current_quantity + 1 > product.stock`, add an error message and redirect without calling `cart.add`
    - _Bug_Condition: isBugCondition_1_5(input) where current_cart_quantity + 1 > product.stock_
    - _Expected_Behavior: reject addition, leave cart quantity unchanged, display error indicating max available quantity_
    - _Preservation: add within stock limit must continue to increment cart correctly (3.3)_
    - _Requirements: 2.5, 3.3_

  - [x] 7.2 Fix Bug 1.6 — Cart.__len__ Counts Inactive Products
    - File: `store/cart.py`, function `Cart.__len__`
    - Query active product IDs: `active_ids = set(str(pk) for pk in Product.objects.filter(id__in=self.cart.keys(), is_active=True).values_list('id', flat=True))`
    - Sum quantities only for items whose ID is in `active_ids`
    - _Bug_Condition: isBugCondition_1_6(input) where inactive product IDs exist in session cart_
    - _Expected_Behavior: len(cart) returns only sum of quantities for active products_
    - _Preservation: Cart.__iter__ behavior (filter inactive, populate removed_items) must remain unchanged (3.4)_
    - _Requirements: 2.6, 3.4_

  - [x] 7.3 Fix Bug 1.7 — Cart Mutation via GET Request
    - File: `store/views/cart.py`, functions `add_to_cart` and `remove_from_cart`
    - Add `@require_POST` decorator to both views (import from `django.views.decorators.http`)
    - Update any template `<a href>` links for add/remove to use `<form method="post">` with `{% csrf_token %}`
    - _Bug_Condition: isBugCondition_1_7(input) where input.method == 'GET'_
    - _Expected_Behavior: GET /cart/add/<pk>/ and /cart/remove/<pk>/ return 405, cart unchanged_
    - _Preservation: POST add/remove with CSRF token must continue to mutate cart correctly_
    - _Requirements: 2.7_

  - [x] 7.4 Verify bug condition exploration tests now pass (Group B)
    - **Property 1: Expected Behavior** - Cart Logic Bugs Fixed
    - **IMPORTANT**: Re-run the SAME tests from task 5 — do NOT write new tests
    - Run all three bug condition tests from task 5 on FIXED code
    - **EXPECTED OUTCOME**: All three tests PASS (confirms bugs 1.5–1.7 are fixed)
    - _Requirements: 2.5, 2.6, 2.7_

  - [x] 7.5 Verify preservation tests still pass (Group B)
    - **Property 2: Preservation** - Cart Logic Preservation
    - **IMPORTANT**: Re-run the SAME tests from task 6 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in cart add/remove/iter/len flows)

- [x] 8. Checkpoint — Group B all tests pass
  - Ensure all Group B exploration and preservation tests pass; ask the user if questions arise

---

## Group C — Data Integrity / UX (Bugs 1.8–1.11)

- [x] 9. Write bug condition exploration tests — Group C Data Integrity / UX
  - **Property 1: Bug Condition** - Data/UX Bugs (Missing Email, Slug Leak, Broken Password Reset, Non-functional Newsletter)
  - **CRITICAL**: These tests MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **GOAL**: Surface counterexamples that demonstrate each data/UX bug exists
  - **Bug 1.8 — Missing Email:** Submit `SignUpForm` with `email=''`; assert the form is valid and user is created on unfixed code (isBugCondition_1_8: email is null or empty)
  - **Bug 1.9 — Slug Leak:** Request `/product/<pk>/redirect/` for an inactive product; assert response is 302 (not 404) on unfixed code (isBugCondition_1_9: product exists AND is_active=False)
  - **Bug 1.10 — Broken Password Reset:** Parse the login template and assert the "Forgot Password?" href is `#` on unfixed code (isBugCondition_1_10: href == '#' or does not resolve)
  - **Bug 1.11 — Newsletter Form:** Parse the footer template and assert the newsletter input has no enclosing `<form>` element on unfixed code (isBugCondition_1_11: no form element, no action URL, no backend handler)
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.8, 1.9, 1.10, 1.11_

- [x] 10. Write preservation property tests — Group C Data Integrity / UX (BEFORE implementing fixes)
  - **Property 2: Preservation** - Valid Signup, Active Product Redirect, Other Template Elements
  - **IMPORTANT**: Follow observation-first methodology
  - **Bug 1.8 preservation:** Submit `SignUpForm` with valid email → observe account created and email stored; write test asserting valid-email signup continues to work (isBugCondition_1_8 returns false)
  - **Bug 1.9 preservation:** Request `/product/<pk>/redirect/` for an active product → observe 302 to slug URL; write test asserting active product redirect still works (isBugCondition_1_9 returns false)
  - **Bug 1.10 preservation:** Verify other login page elements are unaffected by template change
  - **Bug 1.11 preservation:** Verify other footer elements are unaffected by newsletter form change
  - **Order email preservation (3.7):** Confirm order status change email is still sent when customer has email on file
  - Verify all preservation tests PASS on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.5, 3.7_

- [x] 11. Fix Group C — Data Integrity / UX bugs

  - [x] 11.1 Fix Bug 1.8 — Missing Email Silences Order Notifications
    - File: `store/forms.py`, class `SignUpForm`
    - Set `self.fields['email'].required = True` in `__init__` or via field declaration
    - Optionally use `forms.EmailField` override to enforce format
    - _Bug_Condition: isBugCondition_1_8(input) where input.email is null or empty_
    - _Expected_Behavior: SignUpForm rejects submission with validation error requiring valid email_
    - _Preservation: signup with valid email must continue to create account and store email (3.7)_
    - _Requirements: 2.8, 3.7_

  - [x] 11.2 Fix Bug 1.9 — Inactive Product Slug Leaked via Redirect
    - File: `store/views/products.py`, function `product_detail_by_pk`
    - Change `get_object_or_404(Product, pk=pk)` to `get_object_or_404(Product, pk=pk, is_active=True)`
    - _Bug_Condition: isBugCondition_1_9(input) where product exists AND is_active=False_
    - _Expected_Behavior: returns 404 without issuing redirect or revealing slug_
    - _Preservation: active product PK redirect must continue to redirect to slug URL (3.5)_
    - _Requirements: 2.9, 3.5_

  - [x] 11.3 Fix Bug 1.10 — Broken Password Reset Link
    - File: `core/urls.py` — add `path('accounts/', include('django.contrib.auth.urls'))`
    - File: login template — replace `href="#"` with `href="{% url 'password_reset' %}"`
    - Optionally create custom templates under `templates/registration/` to match site design
    - _Bug_Condition: isBugCondition_1_10 where forgot-password href == '#' or does not resolve_
    - _Expected_Behavior: "Forgot Password?" link resolves to a valid URL leading to a functional password reset flow_
    - _Preservation: other login page elements unaffected_
    - _Requirements: 2.10_

  - [x] 11.4 Fix Bug 1.11 — Non-functional Newsletter Form
    - Option A (preferred): Create `newsletter_subscribe` view accepting POST, validate email, save/process subscription, return success response; add URL `path('newsletter/subscribe/', newsletter_subscribe, name='newsletter_subscribe')`; wrap footer input in `<form method="post" action="{% url 'newsletter_subscribe' %}">` with `{% csrf_token %}`
    - Option B (alternative): Remove the newsletter input from the footer template entirely to eliminate misleading UI
    - _Bug_Condition: isBugCondition_1_11 where no form element, no action URL, no backend handler_
    - _Expected_Behavior: submission is processed with confirmation (Option A) OR input is absent (Option B)_
    - _Preservation: other footer elements unaffected_
    - _Requirements: 2.11_

  - [x] 11.5 Verify bug condition exploration tests now pass (Group C)
    - **Property 1: Expected Behavior** - Data/UX Bugs Fixed
    - **IMPORTANT**: Re-run the SAME tests from task 9 — do NOT write new tests
    - Run all four bug condition tests from task 9 on FIXED code
    - **EXPECTED OUTCOME**: All four tests PASS (confirms bugs 1.8–1.11 are fixed)
    - _Requirements: 2.8, 2.9, 2.10, 2.11_

  - [x] 11.6 Verify preservation tests still pass (Group C)
    - **Property 2: Preservation** - Data/UX Preservation
    - **IMPORTANT**: Re-run the SAME tests from task 10 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in signup, product redirect, order email, and template flows)

- [x] 12. Checkpoint — Group C all tests pass
  - Ensure all Group C exploration and preservation tests pass; ask the user if questions arise

---

## Final Checkpoint

- [x] 13. Full regression pass — all 11 bugs fixed, all tests green
  - Run the complete test suite covering all three groups
  - Confirm all bug condition exploration tests pass (bugs are fixed)
  - Confirm all preservation tests pass (no regressions)
  - Confirm checkout, order history, product search, custom request, and admin flows are unaffected (Requirements 3.6, 3.8, 3.9, 3.10)
  - Ask the user if any questions arise before closing the spec
