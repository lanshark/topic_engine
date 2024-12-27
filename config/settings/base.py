import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Logging configuration
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Django logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
        'workflow': {
            # Make workflow_id optional in the format
            'format': '{asctime} [{levelname}] {name}: {workflow_id}{message}',
            'style': '{',
            'defaults': {'workflow_id': ''}  # Default empty string if no workflow_id
        }
    },
    'filters': {
        'has_workflow_id': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: hasattr(record, 'workflow_id')
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'topic_engine.log'),
            'formatter': 'verbose',
            'maxBytes': 10_485_760,  # 10MB
            'backupCount': 5,
        },
        'workflow_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'workflow.log'),
            'formatter': 'workflow',
            'filters': ['has_workflow_id'],
            'maxBytes': 10_485_760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        # Django's default loggers
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        # Topic Engine loggers
        'topic_engine': {
            'handlers': ['console', 'file'],  # Remove workflow_file from default handlers
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'topic_engine.content': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'topic_engine.topics': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'topic_engine.sources': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Environment variables
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = []

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
]

THIRD_PARTY_APPS = [
    'django_extensions',
    # 'django_htmx',  # We'll add this later
]

LOCAL_APPS = [
    'core.apps.CoreConfig',
    'sources.apps.SourcesConfig',
    'topics.apps.TopicsConfig',
    'content.apps.ContentConfig',
    'output.apps.OutputConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST', default='localhost'),
        'PORT': env('POSTGRES_PORT', default='5432'),
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
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
