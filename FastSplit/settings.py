"""Django settings for FastSplit.

This file keeps the original project configuration (apps/security/static/etc.)
and adds minimal Render support via environment variables.
"""

from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_csv(name: str, default: list[str] | None = None) -> list[str]:
    val = os.getenv(name)
    if val is None:
        return default or []
    return [item.strip() for item in val.split(",") if item.strip()]


def _normalize_hosts(items: list[str]) -> list[str]:
    out: list[str] = []
    for h in items:
        h = h.strip()
        if not h:
            continue
        h = h.replace("http://", "").replace("https://", "")
        out.append(h)
    return out


def _normalize_csrf_origins(items: list[str]) -> list[str]:
    out: list[str] = []
    for o in items:
        o = o.strip()
        if not o:
            continue
        # Django requires scheme in CSRF_TRUSTED_ORIGINS
        if o.startswith("http://") or o.startswith("https://"):
            out.append(o)
        else:
            out.append(f"https://{o}")
    return out


# SECURITY WARNING: keep the secret key used in production secret!
# Render: set SECRET_KEY in Environment.
SECRET_KEY = (
    os.getenv("SECRET_KEY")
    or os.getenv("DJANGO_SECRET_KEY")
    or "django-insecure-"
)

# SECURITY WARNING: don't run with debug turned on in production!
# Render: set DEBUG=False in Environment.
DEBUG = _env_bool("DEBUG", _env_bool("DJANGO_DEBUG", True))


# Allowed hosts
# Render requirement: read from env ALLOWED_HOSTS (comma-separated) and default allow
# fastsplit.onrender.com, localhost, 127.0.0.1.
_default_allowed_hosts = {"fastsplit.onrender.com", "localhost", "127.0.0.1"}
_default_allowed_hosts.update(_normalize_hosts(_env_csv("ALLOWED_HOSTS", [])))
# Backward compat: older local setups
_default_allowed_hosts.update(_normalize_hosts(_env_csv("DJANGO_ALLOWED_HOSTS", [])))
ALLOWED_HOSTS = sorted(_default_allowed_hosts)


# CSRF trusted origins
# Render requirement: read from env CSRF_TRUSTED_ORIGINS (comma-separated) and default
# allow https://fastsplit.onrender.com.
_default_csrf_trusted = {"https://fastsplit.onrender.com"}
_default_csrf_trusted.update(_normalize_csrf_origins(_env_csv("CSRF_TRUSTED_ORIGINS", [])))
CSRF_TRUSTED_ORIGINS = sorted(_default_csrf_trusted)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Security / hardening
    "axes",
    "django_recaptcha",
    "csp",

    # Project apps
    "EsSplit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    # Axes middleware must be early (before auth)
    "axes.middleware.AxesMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Content Security Policy headers
    "csp.middleware.CSPMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "axes.backends.AxesStandaloneBackend",
]

ROOT_URLCONF = "FastSplit.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "FastSplit.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGOUT_REDIRECT_URL = "login"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "axes": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}


# ==========================================
# KONFIGURACJA ZABEZPIECZEŃ
# ==========================================

# AXES (blokowanie po nieudanych próbach)
AXES_ENABLED = _env_bool("AXES_ENABLED", False)
AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = 0.25
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_BY = "combination_user_and_ip"

# Progresywna blokada logowania (nasza logika, niezależna od Axes)
LOGIN_FAILURE_LIMIT = 3
LOGIN_LOCKOUT_SCHEDULE_MINUTES = [1, 5, 10, 15]


# reCAPTCHA (Google v2 Checkbox)
RECAPTCHA_PUBLIC_KEY = os.getenv(
    "RECAPTCHA_PUBLIC_KEY",
    # Google test key (dev-only)
    "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
)
RECAPTCHA_PRIVATE_KEY = os.getenv(
    "RECAPTCHA_PRIVATE_KEY",
    # Google test key (dev-only)
    "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
)
RECAPTCHA_USE_SSL = _env_bool("RECAPTCHA_USE_SSL", False)

# Allow Google test keys in dev
SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]


# CSP headers (django-csp >= 4.0)
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'",),
        "script-src": (
            "'self'",
            "https://code.jquery.com",
            "https://code.jquery.com/ui",
            "https://www.google.com/recaptcha/",
            "https://www.gstatic.com/recaptcha/",
            "'unsafe-inline'",
        ),
        "style-src": (
            "'self'",
            "https://cdnjs.cloudflare.com",
            "https://www.google.com/recaptcha/",
            "'unsafe-inline'",
        ),
        "img-src": ("'self'", "data:", "https:", "https://www.gstatic.com"),
        "font-src": ("'self'", "https://cdnjs.cloudflare.com"),
        "connect-src": ("'self'", "https:", "https://www.google.com/recaptcha/"),
        "frame-src": ("https://www.google.com/recaptcha/",),
        "frame-ancestors": ("'self'",),
    }
}

CONTENT_SECURITY_POLICY_REPORT_ONLY = False


SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = False
