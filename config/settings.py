import os
from pathlib import Path
from datetime import timedelta
import urllib.parse as urlparse
from decouple import AutoConfig

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# AutoConfig reads real environment variables first (used by Render/Heroku),
# then falls back to local.env / .env in BASE_DIR.
config = AutoConfig(search_path=BASE_DIR)

SECRET_KEY = config("SECRET_KEY", default="django-insecure-%_aijh#dbhvhuzm5!9+1!!tnqjzgg9k-a)i6zi+r#y57c=49g%")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0", cast=lambda v: [s.strip() for s in v.split(",")])

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third Party Apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",

    # Internal Apps
    "apps.common",
    "apps.users",
    "apps.salons",
    "apps.employees",
    "apps.scheduling",
    "apps.appointments",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware", # Must be before common
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database Configuration
db_url = config("DATABASE_URL", default="")
if db_url:
    url = urlparse.urlparse(db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Custom User Model
AUTH_USER_MODEL = "users.CustomUser"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ==========================
# Static & Media Files Configuration
# ==========================
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))

# ==========================
# AWS S3 Storage (django-storages + boto3)
# ==========================
# Credentials are read from environment variables ONLY - never hardcoded.
# (See .env.example / render.env.example for the full list of keys.)
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="eu-north-1")

# Use S3 for uploaded media whenever a bucket name is configured; otherwise
# fall back to the local filesystem (e.g. local dev / CI without AWS creds).
_USE_S3_MEDIA = bool(AWS_STORAGE_BUCKET_NAME)

if _USE_S3_MEDIA:
    # Let the existing bucket policy / IAM permissions govern object access.
    # We never try to set ACLs on objects, so the bucket must not be (and is
    # not) publicly writable - the backend credentials do the uploading.
    AWS_DEFAULT_ACL = None
    # Serve plain, unsigned object URLs (the bucket policy already exposes
    # them publicly) so the API returns clean https://...amazonaws.com URLs.
    AWS_QUERYSTRING_AUTH = False
    MEDIA_URL = (
        f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"
    )

# Images arrive as base64 strings inside JSON payloads (see apps.common.fields).
# The Django default of 2.5 MB would silently reject them, so raise it.
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# Maximum size (bytes) of a decoded image accepted by Base64ImageField.
IMAGE_MAX_BYTES = config("IMAGE_MAX_BYTES", default=10 * 1024 * 1024, cast=int)

STORAGES = {
    "default": {
        "BACKEND": (
            "storages.backends.s3.S3Storage"
            if _USE_S3_MEDIA
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "apps.common.renderers.ApiResponseRenderer",
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

# SimpleJWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# OpenAPI / Swagger configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "Salon Management API",
    "DESCRIPTION": "API documentation for the Salon Management backend application.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "ENUM_NAME_OVERRIDES": {
        "AppointmentStatus": "apps.appointments.models.Appointment.STATUS_CHOICES",
        "AvailabilityStatus": "apps.scheduling.models.EmployeeAvailability.STATUS_CHOICES",
        "Gender": "apps.users.models.Customer.GENDER_CHOICES",
        "UserRole": "apps.users.models.CustomUser.ROLE_CHOICES",
        "GenderType": "apps.salons.models.Salon.GENDER_TYPE_CHOICES",
        "SalonStatus": "apps.salons.models.Salon.STATUS_CHOICES",
        "PreferredNotification": "apps.users.models.Customer.NOTIFICATION_CHOICES",
    },
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True

# ==========================
# Production Security
# ==========================
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
    CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)