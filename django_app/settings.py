"""
Django settings for the Vehicle Damage & Insurance Claim project.

Reads all sensitive values from environment variables via django-environ.
Never hardcode secrets here.
"""

import os
from pathlib import Path

import environ

# ── Base paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent   # django_app/

# ── Environment ───────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

# Read .env from the repo root
environ.Env.read_env(BASE_DIR / ".env")

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY", default="django-insecure-vehicle-damage-dev-key-!#2026")
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "*"])

# ── Application definition ───────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # django-allauth (requires sites framework)
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Our apps
    "core",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # allauth account middleware (required since allauth 0.56+)
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "django_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Look for templates in the repo-root templates/ folder first,
        # then in each app's templates/ subfolder.
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

WSGI_APPLICATION = "django_app.wsgi.application"

# ── Database — PostgreSQL with SQLite fallback ────────────────────────────────
_db_engine = env("DB_ENGINE", default="")
if _db_engine == "postgresql" or env("DB_NAME", default="") and env("DB_PASSWORD", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="vehicle_damage_db"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
            "OPTIONS": {
                "client_encoding": "UTF8",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "database" / "vehicle_damage.sqlite3",
        }
    }

# ── Authentication ────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "core.User"

AUTHENTICATION_BACKENDS = [
    # Default Django backend (for admin / username+password)
    "django.contrib.auth.backends.ModelBackend",
    # allauth-specific backend
    "allauth.account.auth_backends.AuthenticationBackend",
]

# allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "none"   # skip e-mail confirmation for Google OAuth flow

LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"
LOGIN_URL = "core:login"

# Google OAuth provider config — credentials loaded from env
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": env("GOOGLE_CLIENT_ID", default=""),
            "secret": env("GOOGLE_CLIENT_SECRET", default=""),
            "key": "",
        },
    }
}

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ── Media / File uploads → AWS S3 ────────────────────────────────────────────
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None          # bucket-owner-full-control; no public ACL
AWS_S3_VERIFY = True
# Generate pre-signed URLs so objects can stay private
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600   # 1 hour

# Use S3 for media only when credentials are present (local fallback for dev)
if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION_NAME,
                "file_overwrite": False,
                "querystring_auth": True,
                "querystring_expire": 3600,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"
else:
    # Local development fallback
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "static" / "uploads"

# ── Gemini API (Multi-Key Failover) ───────────────────────────────────────────
GEMINI_API_KEY_1 = env("GEMINI_API_KEY_1", default="")
GEMINI_API_KEY_2 = env("GEMINI_API_KEY_2", default="")
GEMINI_API_KEY_3 = env("GEMINI_API_KEY_3", default="")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

# Filter non-empty keys in priority order
_gemini_keys = [k for k in [GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3] if k.strip()]
if not _gemini_keys and GEMINI_API_KEY.strip():
    _gemini_keys = [GEMINI_API_KEY.strip()]
GEMINI_API_KEYS = _gemini_keys

# ── Cache Backend (for key cooldown sharing & chat rate-limiting) ─────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "claimsense-cache",
        "TIMEOUT": 300,
    }
}

# ── File upload limits ────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB

# ── Default primary key ───────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
