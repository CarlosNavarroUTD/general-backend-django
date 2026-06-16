# settings/development.py
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# En desarrollo, el link del email de verificación apunta al frontend local
FRONTEND_URL = 'http://localhost:3013'

