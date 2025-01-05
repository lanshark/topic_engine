from pathlib import Path

from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(f"BASE_DIR: {BASE_DIR}")

# Logging configuration
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)

DATA_DIR = config("DATA_DIR", default="/data/")

TOPIC_ENGINE_ENV = config("TOPIC_ENGINE_ENV", default="local")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1", cast=Csv())

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS = [
    "django_extensions",
    # 'django_htmx',  # We'll add this later
]

LOCAL_APPS = [
    "core.apps.CoreConfig",
    "sources.apps.SourcesConfig",
    "topics.apps.TopicsConfig",
    "content.apps.ContentConfig",
    "output.apps.OutputConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": config("POSTGRES_DB", default="topic_engine"),
        "USER": config("POSTGRES_USER", default="topic_engine"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
        "workflow": {
            # Make workflow_id optional in the format
            "format": "{asctime} [{levelname}] {name}: {workflow_id}{message}",
            "style": "{",
            "defaults": {"workflow_id": ""},  # Default empty string if no workflow_id
        },
    },
    "filters": {
        "has_workflow_id": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: hasattr(record, "workflow_id"),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "topic_engine.log"),
            "formatter": "verbose",
            "maxBytes": 10_485_760,  # 10MB
            "backupCount": 5,
        },
        "workflow_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "workflow.log"),
            "formatter": "workflow",
            "filters": ["has_workflow_id"],
            "maxBytes": 10_485_760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        # Django's default loggers
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
        # Topic Engine loggers
        "topic_engine": {
            "handlers": [
                "console",
                "file",
            ],  # Remove workflow_file from default handlers
            "level": config("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "topic_engine.content": {
            "handlers": ["console", "file"],
            "level": config("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "topic_engine.topics": {
            "handlers": ["console", "file"],
            "level": config("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "topic_engine.sources": {
            "handlers": ["console", "file"],
            "level": config("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}

if TOPIC_ENGINE_ENV == "local":
    DEBUG = config("DEBUG", default=True)
    ALLOWED_HOSTS = config(
        "ALLOWED_HOSTS",
        default=["localhost", "127.0.0.1"],
        cast=Csv(),
    )

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = config(
        "SECRET_KEY",
        default="django-insecure-#(62((es!xv$o@-llyeaxb)7pxvsisjquxhfnt4g93&ora9+jk",
    )

    # Update logging for local development
    LOGGING["loggers"]["topic_engine"]["level"] = "DEBUG"
    LOGGING["loggers"]["topic_engine.content"]["level"] = "DEBUG"
    LOGGING["loggers"]["topic_engine.topics"]["level"] = "DEBUG"
    LOGGING["loggers"]["topic_engine.sources"]["level"] = "DEBUG"

    # Ensure console logging is enabled
    if "console" not in LOGGING["handlers"]:
        LOGGING["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }

    for logger in LOGGING["loggers"].values():
        if "console" not in logger["handlers"]:
            logger["handlers"].append("console")

if TOPIC_ENGINE_ENV == "production":
    DEBUG = False
    ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

    # Security
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Update logging for production
    LOGGING["loggers"]["topic_engine"]["level"] = "INFO"
    LOGGING["loggers"]["topic_engine.content"]["level"] = "INFO"
    LOGGING["loggers"]["topic_engine.topics"]["level"] = "INFO"
    LOGGING["loggers"]["topic_engine.sources"]["level"] = "INFO"

    # Disable console logging in production
    for logger in LOGGING["loggers"].values():
        if "console" in logger["handlers"]:
            logger["handlers"].remove("console")

    # Optionally add other production-specific handlers (like syslog)
    # LOGGING['handlers']['syslog'] = {
    #     'class': 'logging.handlers.SysLogHandler',
    #     'formatter': 'verbose',
    #     'facility': 'local7',
    #     'address': '/dev/log',
    # }

if TOPIC_ENGINE_ENV == "test":
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
        def __contains__(self, _):
            return True

        def __getitem__(self, _):
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
