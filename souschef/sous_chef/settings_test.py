from .settings import *  # noqa


SECRET_KEY = "SecretKeyForUseOnTravis"

DEBUG = False
TEMPLATE_DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
