import os

from .base import *  # noqa: F401,F403


if os.getenv('USE_SQLITE_DEV', 'False').lower() == 'true':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
