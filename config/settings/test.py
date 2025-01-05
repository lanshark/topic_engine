from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "topic_engine_test",
        "USER": "test",  # Replace with your database user
        "PASSWORD": "CHANGE_ME!",  # Replace with your database password
        "HOST": "localhost",
        "PORT": "5432",
        "TEST": {
            "TEMPLATE": "template_postgis",
            "SERIALIZE": False,  # Speeds up test runs
        },
        "OPTIONS": {"sslmode": "disable"},
    },
}

# Test runner settings
TEST_RUNNER = "django.test.runner.DiscoverRunner"


# Disable migrations during testing for speed
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Cache settings for testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# Media settings for testing
MEDIA_ROOT = BASE_DIR / "test_media"

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}
