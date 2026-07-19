from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Dev settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery: Run tasks synchronously in dev/tests to avoid needing a running Redis server
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Cache: Use local memory cache for local development to avoid requiring a running Redis server
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'resolv-local-dev-cache',
        'KEY_PREFIX': 'resolv_dev',
    }
}

