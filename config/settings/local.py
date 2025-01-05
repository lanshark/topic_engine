from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-#(62((es!xv$o@-llyeaxb)7pxvsisjquxhfnt4g93&ora9+jk"

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
