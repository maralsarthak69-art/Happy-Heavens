import os
from pathlib import Path
import dj_database_url
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Robust pathing: Points exactly to the .env file in your root directory
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY: Pull these directly from your .env file
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

# Environment Detection (Render/Local)
IS_HEROKU = "RENDER" in os.environ

ALLOWED_HOSTS = ['*']

# Auth Redirects
LOGIN_URL = 'login'              
LOGIN_REDIRECT_URL = 'home'      
LOGOUT_REDIRECT_URL = 'home'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',  # Cloudinary storage must come before staticfiles
    'django.contrib.staticfiles',
    'cloudinary',          # Cloudinary integration
    'store',               # Your main app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise is active only on Render for production static files
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if IS_HEROKU else []),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

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

# 2. Database Configuration
if not IS_HEROKU:
    # LOCAL: Connects to your pgAdmin 'happy_heavens_db'
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'happy_heavens_db',
            'USER': 'postgres',
            'PASSWORD': 'root123',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
else:
    # PRODUCTION: Connects to Render Cloud DB
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600
        )
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 3. Static & Media Configuration
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Production Storage settings
if IS_HEROKU:
    # UPDATED: Switched from CompressedManifestStaticFilesStorage to CompressedStaticFilesStorage
    # This ignores missing GIS/Admin icons that were causing the build to fail
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
    
    # Use Cloudinary for Media files (images) only in production/Render
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Cloudinary Credentials (Optional: can also use CLOUDINARY_URL in .env)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUD_NAME', default=''),
    'API_KEY': env('API_KEY', default=''),
    'API_SECRET': env('API_SECRET', default=''),
}

# Local Media (Used locally unless you want to test Cloudinary on your laptop)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 4. Session Settings
SESSION_COOKIE_AGE = 604800 
SESSION_SAVE_EVERY_REQUEST = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
