from .base import *

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
