# Happy Heavens

Happy Heavens is a handcrafted-gifts and luxury-essentials e-commerce website for customers in Pune, India. It is built as a single Django application with server-rendered pages, a session-backed shopping cart, authenticated checkout, inventory management, an owner dashboard, Django Admin, and email/WhatsApp order notifications.

## Highlights

- Product catalogue with categories, search, pagination, product images, stock visibility, and active/inactive product controls.
- Guest shopping cart stored in the Django session.
- Account registration, login, logout, and order history.
- QR-code payment with payment-proof upload and Cash on Delivery.
- Transactional order creation with row locking and stock validation to prevent overselling.
- Custom-gift request form with optional reference image uploads.
- Newsletter subscription capture.
- Staff dashboard for orders, statuses, private notes, stock, products, and CSV export.
- Customized Django Admin with product image previews and multi-image upload support.
- Email and Twilio WhatsApp notifications for new orders, custom requests, and order-status changes.
- SEO endpoints for `robots.txt` and a generated XML sitemap.
- Production static files through WhiteNoise and production media files through Cloudinary.
- Render deployment configuration with PostgreSQL/Supabase support.

## Technology Stack

### Backend

- Python 3.12
- Django 4.2.11
- PostgreSQL in production and standard non-test deployments
- SQLite support for local development and tests through `USE_SQLITE=true`
- `psycopg` / `psycopg-binary` for PostgreSQL
- `django-environ` for environment configuration
- `dj-database-url` for `DATABASE_URL` parsing
- Django sessions, authentication, admin, messages, forms, ORM, migrations, and signals

### Frontend

- Django Templates
- Tailwind CSS loaded from the templates/CDN rather than a compiled frontend application
- Vanilla HTML/CSS/JavaScript enhancements
- Microsoft Clarity package metadata is present in `package.json`; Node is not used to build or serve the application

### Infrastructure and integrations

- Gunicorn for WSGI serving
- WhiteNoise for compressed static files
- Cloudinary for production media storage
- SMTP email in production and console email in local debug mode
- Twilio WhatsApp API for notifications
- Render deployment configuration
- Docker support

## Architecture

This is a monolithic, server-rendered Django application. There is no separate REST API, SPA frontend, or microservice layer.

```text
Browser
  |
  v
Gunicorn / Django
  |
  +-- core/                  Project settings, WSGI/ASGI, root URL configuration
  |
  +-- store/                 Main e-commerce Django app
  |     +-- models.py        Catalogue, orders, requests, newsletter models
  |     +-- views/           Customer, checkout, dashboard, SEO, and auth views
  |     +-- services/        Transactional order logic and Twilio notifications
  |     +-- cart.py          Session-backed cart
  |     +-- forms.py         Checkout, auth, and customization forms
  |     +-- signals.py       Emails, WhatsApp status updates, cache invalidation
  |     +-- admin.py         Store management interface
  |
  +-- templates/             Server-rendered HTML pages
  +-- static/                Source static assets
  +-- media/                 Local development uploads
  +-- PostgreSQL/SQLite      Relational application data
  +-- Cloudinary             Production uploads
```

### Request and order flow

1. A visitor browses active products and adds items to the session cart.
2. Checkout requires an authenticated account.
3. The checkout form validates delivery details and requires a screenshot when QR payment is selected.
4. `store.services.order_service.create_order` runs inside `transaction.atomic()`.
5. Products are locked with `select_for_update()`, stock is checked, and inventory is decremented.
6. The `Order` and its price-locked `OrderItem` records are created.
7. The cart is cleared only after successful order creation.
8. The owner can update the order status from the dashboard or Django Admin.
9. Status changes trigger customer email and WhatsApp notifications.

## Project Structure

```text
.
├── core/
│   ├── settings.py          Environment, database, security, email, storage, and cache settings
│   ├── urls.py              Root routes, admin, auth routes, and custom error handlers
│   ├── asgi.py
│   └── wsgi.py
├── store/
│   ├── models.py            Domain models
│   ├── admin.py             Customized Django Admin
│   ├── cart.py              Session cart implementation
│   ├── forms.py             Customer-facing forms
│   ├── middleware.py        Staff inactivity timeout
│   ├── signals.py           Notifications and cache invalidation
│   ├── urls.py              Application routes
│   ├── views/               Feature-specific views
│   ├── services/            Order and WhatsApp services
│   ├── migrations/           Database migrations
│   └── management/commands/  Cache and WhatsApp utility commands
├── templates/               Storefront, auth, error, and dashboard templates
├── static/                  Source CSS, JavaScript, images, and videos
├── media/                   Local uploaded media
├── tests/                   Settings and CSRF regression/property tests
├── requirements.txt         Python dependencies
├── manage.py                Django command entry point
├── build.sh                 Render build and migration script
├── render.yaml              Render service definition
├── Dockerfile               Container image definition
└── Procfile                 Process command for compatible hosts
```

## Data Model

| Model | Purpose |
| --- | --- |
| `Category` | Product grouping with a unique URL slug |
| `Product` | Name, description, price, stock, category, visibility, and creation date |
| `ProductImage` | One-to-many gallery images for products |
| `Order` | Customer, delivery details, payment method/proof, total, status, notes, and timestamps |
| `OrderItem` | Products purchased, quantity, and price locked at purchase time |
| `CustomRequest` | Customer idea, contact details, and optional reference image |
| `NewsletterSubscriber` | Unique email subscribers and subscription timestamp |

Order statuses are `PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, and `REJECTED`. Payment methods are `QR` and `COD`.

## Pages and Routes

### Public storefront

| URL | Purpose |
| --- | --- |
| `/` | Home page, hero section, new arrivals, and paginated product grid |
| `/product/<slug>/` | Product detail page |
| `/product/<id>/redirect/` | Legacy ID route that redirects to the product slug |
| `/category/<slug>/` | Paginated category listing |
| `/search/?q=<query>` | Search product names, descriptions, and category names |
| `/cart/` | Cart summary |
| `/cart/add/<id>/` | Add a product to the cart |
| `/cart/remove/<id>/` | Remove a product from the cart |
| `/customize/` | Submit a custom-gift idea |
| `/customize/success/` | Custom-request confirmation |
| `/newsletter/subscribe/` | Newsletter subscription POST endpoint |
| `/robots.txt` | Crawler rules |
| `/sitemap.xml` | Generated public-page sitemap |

### Customer account and orders

| URL | Purpose |
| --- | --- |
| `/signup/` | Create an account |
| `/login/` | Sign in |
| `/logout/` | POST-only logout |
| `/checkout/` | Authenticated QR/COD checkout |
| `/checkout/success/<id>/` | Order confirmation |
| `/orders/` | Authenticated customer's orders |
| `/orders/<id>/` | Authenticated order detail |
| `/accounts/` | Django's built-in password-reset URL namespace |

### Staff dashboard and administration

| URL | Purpose |
| --- | --- |
| `/dashboard/` | Sales overview, recent orders, requests, and low-stock products |
| `/dashboard/order/<id>/update/` | Update order status and private notes |
| `/dashboard/stock/` | Stock manager |
| `/dashboard/stock/<id>/update/` | Update product stock |
| `/dashboard/products/` | Product quick-edit view |
| `/dashboard/products/<id>/update/` | Update product details |
| `/dashboard/export/orders.csv` | Export orders as CSV |
| `/dashboard/guide/` | Owner usage guide |
| `/admin/` | Full Django Admin |

Dashboard routes require a staff account. Staff and superuser sessions expire after two hours of inactivity.

## Local Development

### Prerequisites

- Python 3.12
- Git
- PostgreSQL, or SQLite for a lightweight local setup

### Setup on Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a local `.env` file. Do not commit it or share its values:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
USE_SQLITE=true
ALLOWED_HOST=localhost

# Optional local email settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Optional Cloudinary settings for local media testing
CLOUD_NAME=
API_KEY=
API_SECRET=
```

Initialize the database and create an admin user:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver
```

The site is then available at `http://127.0.0.1:8000/` and the admin is available at `http://127.0.0.1:8000/admin/`.

### Linux/macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Environment Variables

Required in production:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Set to `False` in production |
| `ALLOWED_HOST` | Primary domain without the protocol |
| `DATABASE_URL` | Production PostgreSQL/Supabase pooler connection |
| `DIRECT_URL` | Direct PostgreSQL connection used for migrations/DDL when required |

Media and email:

| Variable | Purpose |
| --- | --- |
| `CLOUD_NAME` | Cloudinary cloud name |
| `API_KEY` | Cloudinary API key |
| `API_SECRET` | Cloudinary API secret |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password/app password |
| `DEFAULT_FROM_EMAIL` | Sender address |
| `STORE_OWNER_EMAIL` | Recipient for custom-request alerts |

WhatsApp notifications:

| Variable | Purpose |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp sender, for example `whatsapp:+14155238886` |
| `ADMIN_WHATSAPP_NUMBER` | Owner/admin WhatsApp destination |

`RENDER=true` enables production-specific database and media-storage behavior. When `DEBUG=False`, `ALLOWED_HOST` is mandatory. If Render supplies `RENDER_EXTERNAL_HOSTNAME`, it is added to allowed hosts and CSRF trusted origins.

## Production Deployment

### Render

The repository includes [`render.yaml`](./render.yaml). Render runs:

```text
Build: ./build.sh
Start: gunicorn core.wsgi:application --workers 2 --threads 2 --timeout 60 --max-requests 1000 --max-requests-jitter 100
```

The build script installs dependencies, removes stale collected static files, runs `collectstatic`, applies migrations, creates the database cache table, clears the cache, and attempts a non-interactive superuser creation.

For Supabase/PostgreSQL, use the pooler URL as `DATABASE_URL` for normal requests and the direct connection as `DIRECT_URL` for migrations and other DDL operations.

### Docker

```bash
docker build -t happy-heavens .
docker run --env-file .env -p 8080:8080 happy-heavens
```

The container uses Python 3.12, installs PostgreSQL build dependencies, runs as a non-root user, and serves Django through Gunicorn on port `8080`.

## Static Files and Media

- Source static assets live in `static/`.
- `collectstatic` writes collected assets to `staticfiles/`.
- WhiteNoise serves compressed static files in production.
- Local uploads are stored below `media/`.
- Production uploads use Cloudinary through `django-cloudinary-storage`.
- Development serves media through Django when `DEBUG=True`.

## Management Commands

```powershell
python manage.py clear_cache
python manage.py test_whatsapp
python manage.py check
python manage.py makemigrations
python manage.py migrate
```

`clear_cache` clears the configured Django cache. `test_whatsapp` is available for checking the Twilio notification integration after the required environment variables are configured.

## Testing

The current test suite focuses on settings and CSRF behavior, including deterministic unit tests and Hypothesis property-based tests:

```powershell
$env:USE_SQLITE = "true"
python manage.py test
```

For a Django system check:

```powershell
python manage.py check
```

Template validation is also available:

```powershell
python validate_templates.py
```

## Security and Operations Notes

- Never commit `.env`, database credentials, Cloudinary credentials, SMTP passwords, or Twilio tokens.
- Keep `DEBUG=False` in production and provide `ALLOWED_HOST`.
- Production settings enable HTTPS redirects, secure cookies, HSTS, clickjacking protection, and content-type sniffing protection.
- Checkout and dashboard mutations use POST requests and Django CSRF protection.
- The cart filters inactive products and removes stale session entries.
- Stock changes during checkout are protected by a database transaction and row-level locking.
- Notification failures are logged and do not roll back a successfully created order.
- The sitemap and `robots.txt` currently use `https://happyheavens.in`; update `store/views/seo.py` if the canonical production domain changes.

## Admin Workflow

1. Create categories in `/admin/store/category/`.
2. Create active products and set their prices and stock.
3. Upload one or more product gallery images from the product admin screen.
4. Monitor new orders from `/dashboard/` or `/admin/store/order/`.
5. Update order status and private notes as the order progresses.
6. Review custom requests and newsletter subscribers in Django Admin.
7. Use the stock manager and CSV export for day-to-day operations.

## License

No license file is currently included in the repository. Add a license before distributing the project or accepting external contributions.
