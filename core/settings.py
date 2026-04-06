import os
from pathlib import Path
import dj_database_url
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# 1. Environment
# ---------------------------------------------------------------------------
env = environ.Env(DEBUG=(bool, False))

# Read .env only when the file exists (local dev).
# On Render the vars are injected directly into os.environ.
_env_file = os.path.join(BASE_DIR, '.env')
if os.path.isfile(_env_file):
    environ.Env.read_env(_env_file)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

# True when running on Render (set RENDER=true in Render dashboard)
IS_PRODUCTION = "RENDER" in os.environ

# ---------------------------------------------------------------------------
# 2. Hosts & CSRF
# ---------------------------------------------------------------------------
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    _allowed_host = env('ALLOWED_HOST', default=None)
    if not _allowed_host:
        raise ImproperlyConfigured(
            "ALLOWED_HOST environment variable is required when DEBUG=False."
        )
    ALLOWED_HOSTS = [_allowed_host, f'www.{_allowed_host}']
    _render_host = env('RENDER_EXTERNAL_HOSTNAME', default=None)
    if _render_host:
        ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS = [
        f'https://{_allowed_host}',
        f'https://www.{_allowed_host}',
    ]

# ---------------------------------------------------------------------------
# 3. Auth
# ---------------------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# ---------------------------------------------------------------------------
# 4. Apps
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',  # staticfiles before cloudinary_storage
    'cloudinary_storage',
    'cloudinary',
    'store',
]

# ---------------------------------------------------------------------------
# 5. Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'store.middleware.AdminSessionTimeoutMiddleware',  # admin timeout after 2hrs inactivity
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# ---------------------------------------------------------------------------
# 6. Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_count',
                'store.context_processors.categories_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ---------------------------------------------------------------------------
# 7. Database
# ---------------------------------------------------------------------------
if not IS_PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='happy_heavens_db'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
else:
    # Supabase via pgBouncer connection pooler (port 6543)
    # conn_max_age=0 is required — pgBouncer handles pooling itself
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL', ''),
            conn_max_age=0,
            ssl_require=True,
        )
    }

# ---------------------------------------------------------------------------
# 8. Cache — database-backed, zero extra services needed
# ---------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

# ---------------------------------------------------------------------------
# 9. Security headers
# ---------------------------------------------------------------------------
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# 10. Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# 11. Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# 12. Static & Media
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Tell cloudinary_storage to only handle MEDIA, not static files
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUD_NAME', default=''),
    'API_KEY': env('API_KEY', default=''),
    'API_SECRET': env('API_SECRET', default=''),
    'STATICFILES': False,  # never let cloudinary touch static files
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ---------------------------------------------------------------------------
# 13. Sessions
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = 604800          # 7 days for regular users
SESSION_SAVE_EVERY_REQUEST = False   # only save when session data actually changes
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Admin session timeout — 2 hours of inactivity logs out staff/superusers
ADMIN_SESSION_TIMEOUT = 60 * 60 * 2  # 2 hours in seconds

# ---------------------------------------------------------------------------
# 14. Email
# ---------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
else:
    EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
STORE_OWNER_EMAIL = env('STORE_OWNER_EMAIL', default=EMAIL_HOST_USER)

# ---------------------------------------------------------------------------
# 15. Misc
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
