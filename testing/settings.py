import os
import sys

import django

sys.path.insert(0, '..')

PROJECT_ROOT = os.path.dirname(__file__)
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'djorm_ext_filtered_contenttypes_%s' % django.get_version(),
        'USER': os.getenv("PGUSER", "postgres"),
        'PASSWORD': os.getenv("PGPASSWORD", ""),
        'HOST': os.getenv("PGHOST", "127.0.0.1"),
        'PORT': os.getenv("PGPORT", "5432"),
    }
}


TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
STATICFILES_DIRS = ()

# Test-only settings key. This is NOT a secret and must never be used in production.
SECRET_KEY = 'not-a-secret-test-only-do-not-use-in-production'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'filtered_contenttypes',
    'filtered_contenttypes.tests',
)

MIDDLEWARE = []
