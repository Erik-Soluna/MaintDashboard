"""
Django settings for maintenance_dashboard project.
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*')
if not isinstance(ALLOWED_HOSTS, list):
    if isinstance(ALLOWED_HOSTS, bool):
        ALLOWED_HOSTS = ['*']
    else:
        ALLOWED_HOSTS = str(ALLOWED_HOSTS)
        ALLOWED_HOSTS = [s.strip() for s in ALLOWED_HOSTS.split(',')]

# Add testserver for Playwright testing
if 'testserver' not in ALLOWED_HOSTS and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'crispy_forms',
    'crispy_bootstrap4',
    'django_filters',
    'django_tables2',
    'widget_tweaks',
    'django_celery_beat',
    # Local apps
    'equipment',
    'maintenance',
    'events',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.DatabaseConnectionMiddleware',
    'core.middleware.SystemMonitoringMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'maintenance_dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_context',
                'core.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'maintenance_dashboard.wsgi.application'

# Database
# Try to use PostgreSQL, fall back to SQLite for development
import os
from django.db import connection

# Check if we're in development and PostgreSQL is not available
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)

if USE_SQLITE or (DEBUG and not os.environ.get('DB_HOST')):
    # Use SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Use PostgreSQL for production
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='maintenance_dashboard'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 300,  # 5 minutes - Django connection pooling setting
            'OPTIONS': {
                # PostgreSQL-specific connection options can go here
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Nginx Proxy Manager / Reverse Proxy Settings
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=True, cast=bool)
USE_X_FORWARDED_PORT = config('USE_X_FORWARDED_PORT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF trusted origins for reverse proxy
CSRF_TRUSTED_ORIGINS = [
    'https://maintenance.errorlog.app',
    'https://localhost',
    'https://127.0.0.1',
]

# Add any additional trusted origins from environment
additional_origins = config('CSRF_TRUSTED_ORIGINS', default='', cast=str)
if additional_origins:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in additional_origins.split(',') if origin.strip()])

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# Celery Configuration
# Try to use Redis, fall back to database if Redis is not available
REDIS_HOST = config('REDIS_HOST', default='redis')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_PASSWORD = config('REDIS_PASSWORD', default='')

# Build Redis URLs with fallback options
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}'

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=f'{REDIS_URL}/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=f'{REDIS_URL}/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'generate-scheduled-maintenance': {
        'task': 'maintenance.tasks.generate_scheduled_maintenance',
        'schedule': 7200.0,  # Every 2 hours (reduced from 1 hour)
    },
    'send-maintenance-reminders': {
        'task': 'maintenance.tasks.send_maintenance_reminders',
        'schedule': 86400.0,  # Daily at midnight
    },
    'check-overdue-maintenance': {
        'task': 'maintenance.tasks.check_overdue_maintenance',
        'schedule': 14400.0,  # Every 4 hours (reduced from 2 hours)
    },
    'send-event-reminders': {
        'task': 'events.tasks.send_event_reminders',
        'schedule': 86400.0,  # Daily
    },
    'generate-maintenance-events': {
        'task': 'events.tasks.generate_maintenance_events',
        'schedule': 7200.0,  # Every 2 hours (reduced from 30 minutes)
    },
    'cleanup-old-events': {
        'task': 'events.tasks.cleanup_old_events',
        'schedule': 604800.0,  # Weekly
    },
}
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Caching Configuration
# Use Redis if available, fall back to database for development
USE_REDIS = config('USE_REDIS', default=True, cast=bool)

# Test Redis connectivity and fall back gracefully
def get_cache_config():
    """Get cache configuration with Redis fallback."""
    if USE_REDIS and not DEBUG:
        # Try Redis for production
        try:
            import redis
            r = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
            r.ping()  # Test connection
            return {
                'default': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': f'{REDIS_URL}/1',
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    },
                    'KEY_PREFIX': 'maintenance_dashboard',
                    'TIMEOUT': 300,  # 5 minutes default timeout
                }
            }, 'django.contrib.sessions.backends.cache'
        except Exception as e:
            print(f"Redis connection failed: {e}. Falling back to database cache.")
    
    # Use database cache as fallback
    try:
        from django.core.cache.backends.db import DatabaseCache
        return {
            'default': {
                'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                'LOCATION': 'cache_table',
            }
        }, 'django.contrib.sessions.backends.db'
    except Exception as e:
        print(f"Database cache failed: {e}. Falling back to dummy cache.")
        return {
            'default': {
                'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        }, 'django.contrib.sessions.backends.db'

CACHES, SESSION_ENGINE = get_cache_config()

SESSION_COOKIE_AGE = 86400  # 24 hours

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@maintenance-dashboard.com')

# System Monitoring Configuration
MONITORING_ENABLED = config('MONITORING_ENABLED', default=True, cast=bool)
MONITORING_SLOW_REQUEST_THRESHOLD = config('MONITORING_SLOW_REQUEST_THRESHOLD', default=5.0, cast=float)
MONITORING_VERY_SLOW_REQUEST_THRESHOLD = config('MONITORING_VERY_SLOW_REQUEST_THRESHOLD', default=10.0, cast=float)
MONITORING_CPU_THRESHOLD = config('MONITORING_CPU_THRESHOLD', default=80.0, cast=float)
MONITORING_MEMORY_THRESHOLD = config('MONITORING_MEMORY_THRESHOLD', default=80.0, cast=float)
MONITORING_DISK_THRESHOLD = config('MONITORING_DISK_THRESHOLD', default=90.0, cast=float)