import os, sys, django

sys.path.insert(0, '..')

PROJECT_ROOT = os.path.dirname(__file__)
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'djorm_ext_filtered_contenttypes_%s' % django.get_version(),
        'USER': os.getenv("PGUSER", "postgres"),
        'PASSWORD': os.getenv("PGPASSWORD", ""),
        'HOST': os.getenv("PGHOST", "127.0.0.1"),
        'PORT': os.getenv("PGPORT", "5432"),
    }
}


if 'TRAVIS' in os.environ:
    DATABASES['default']['NAME'] = 'travisci'
    DATABASES['default']['HOST'] = 'localhost'
    DATABASES['default']['PORT'] = ''


TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

SECRET_KEY = 'di!n($kqa3)nd%ikad#kcjpkd^uw*h%*kj=*pm7$vbo6ir7h=l'
INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'filtered_contenttypes',
    'filtered_contenttypes.tests',
)

if django.VERSION < (1,7):
    TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

MIDDLEWARE_CLASSES = []
