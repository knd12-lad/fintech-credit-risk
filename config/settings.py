"""
Django settings for FinTech Credit Risk project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables (do NOT override already-set shell variables)
load_dotenv(BASE_DIR / ".env")

# 5.1 DEBUG defaults to False
DEBUG = os.getenv("DEBUG", "False").strip().lower() in ("true", "1", "t", "yes")

# 5.1 If DEBUG is False and SECRET_KEY is missing, raise ImproperlyConfigured
SECRET_KEY = os.getenv("SECRET_KEY")
if not DEBUG and not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is required when DEBUG is False.")
if not SECRET_KEY:
    SECRET_KEY = "django-insecure-dev-fallback-key-replace-in-production"

# ALLOWED_HOSTS
allowed_hosts_raw = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_raw.split(",") if h.strip()]

# 5.2 CSRF_TRUSTED_ORIGINS from env (comma separated, ignore empty)
csrf_trusted_raw = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in csrf_trusted_raw.split(",") if origin.strip()
]


# Application definition

INSTALLED_APPS = [
    "risk_app.admin_apps.RiskWiseAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "risk_app",
]

# 5.3 Add whitenoise middleware right after SecurityMiddleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "risk_app.middleware.SplitSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "risk_app.middleware.ViewAsReadOnlyMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "risk_app.context_processors.currency_context",
                "risk_app.context_processors.view_as_context",
            ],
        },
    },
]

CURRENCY_SYMBOL = "$"

WSGI_APPLICATION = "config.wsgi.application"


# Database (MySQL)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# 5.3 Whitenoise and static root configuration

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# 5.4 Production HTTPS and Security Hardening
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    # Site is hosted on a shared hosting subdomain; preload and includeSubDomains are intentionally off
    SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
    X_FRAME_OPTIONS = "DENY"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "risk_app.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

MESSAGE_TAGS = {message_constants.ERROR: "danger"}

# Email Configuration (Phase 6 Preparation)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 25))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").strip().lower() in ("true", "1", "t", "yes")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@riskwise.local")

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"