from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

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


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-6$a=(1$50&jqoqou0@9rv9q784ue_c9(9i9o1es5@f8bepf0_)",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = _env_csv("DJANGO_ALLOWED_HOSTS", [])

# CSRF trusted origins for Render deployment
# Can be set via CSRF_TRUSTED_ORIGINS env var (comma-separated)
# Or auto-configured from RENDER_EXTERNAL_HOSTNAME
CSRF_TRUSTED_ORIGINS = _env_csv("CSRF_TRUSTED_ORIGINS", [])
if not CSRF_TRUSTED_ORIGINS and os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    # Automatically configure for Render if RENDER_EXTERNAL_HOSTNAME is set
    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    CSRF_TRUSTED_ORIGINS = [f"https://{render_hostname}"]

# Render uses a proxy, so we need to trust X-Forwarded-Proto header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # --- NOWE BIBLIOTEKI ZABEZPIECZAJĄCE ---
    'axes',              # Blokowanie po nieudanych logowaniach
    'django_recaptcha',  # Obsługa Captcha
    # ---------------------------------------
    
    'EsSplit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # --- WHITENOISE MIDDLEWARE (Serve static files in production) ---
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ----------------------------------------------------------------
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    # --- AXES MIDDLEWARE (Musi być wysoko, przed uwierzytelnianiem) ---
    'axes.middleware.AxesMiddleware',
    # ------------------------------------------------------------------
    
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # --- CSP MIDDLEWARE (Wysyła Content Security Policy nagłówkami HTTP) ---
    'csp.middleware.CSPMiddleware',
    # -----------------------------------------------------------------------
]

# --- KONFIGURACJA BACKENDÓW LOGOWANIA (Wymagane dla Axes) ---
AUTHENTICATION_BACKENDS = [
    # Domyślny backend Django
    'django.contrib.auth.backends.ModelBackend',
    # Backend Axes
    'axes.backends.AxesStandaloneBackend',
]

ROOT_URLCONF = 'FastSplit.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'FastSplit.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        # Zmieniono na min. 8 znaków (wymóg bezpieczeństwa)
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# WhiteNoise configuration for serving static files in production
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGOUT_REDIRECT_URL = 'login'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        # Dodatkowo logowanie dla Axes, żebyś widział próby włamań w konsoli
        'axes': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# ==========================================
# KONFIGURACJA ZABEZPIECZEŃ (POPRAWIONA)
# ==========================================

# 1. AXES (Blokowanie po 3 nieudanych próbach)
AXES_ENABLED = _env_bool("AXES_ENABLED", False)
AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = 0.25
AXES_RESET_ON_SUCCESS = True

# Progresywna blokada logowania (nasza logika, niezależna od Axes)
LOGIN_FAILURE_LIMIT = 3
LOGIN_LOCKOUT_SCHEDULE_MINUTES = [1, 5, 10, 15]

# Zmiana składni na nowszą (naprawia Warning):
AXES_LOCK_OUT_BY = 'combination_user_and_ip' 

# 2. RECAPTCHA (Google v2 Checkbox - klucze produkcyjne)
RECAPTCHA_PUBLIC_KEY = os.getenv(
    "RECAPTCHA_PUBLIC_KEY",
    "6Lc5sUksAAAAAGPArQ8yi6zBtxIdMRkg-pbHZVQP",
)
RECAPTCHA_PRIVATE_KEY = os.getenv(
    "RECAPTCHA_PRIVATE_KEY",
    "6Lc5sUksAAAAAD1qk76onFmaSv703nW_racq1ppQ",
)
RECAPTCHA_USE_SSL = _env_bool("RECAPTCHA_USE_SSL", False)

# 3. WYCISZENIE BŁĘDÓW (Naprawia Error przy migracji)
# Pozwalamy na używanie kluczy testowych Google w trybie developerskim
# SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']  # Nie potrzebny - używamy prawdziwych kluczy

# 4. SECURITY HEADERS (Ochrona przed atakami XSS, Clickjacking, MIME sniffing)
# Content Security Policy (CSP) - wysyłana przez middleware django-csp
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "https://code.jquery.com",
    "https://code.jquery.com/ui",
    "https://www.google.com/recaptcha/",
    "https://www.gstatic.com/recaptcha/",
    "'unsafe-inline'",
)
CSP_STYLE_SRC = (
    "'self'",
    "https://cdnjs.cloudflare.com",
    "https://www.google.com/recaptcha/",
    "'unsafe-inline'",
)
CSP_IMG_SRC = ("'self'", "data:", "https:", "https://www.gstatic.com")
CSP_FONT_SRC = ("'self'", "https://cdnjs.cloudflare.com")
CSP_CONNECT_SRC = ("'self'", "https:", "https://www.google.com/recaptcha/")
CSP_FRAME_SRC = ("https://www.google.com/recaptcha/",)
CSP_FRAME_ANCESTORS = ("'self'",)

# Wysyłaj rzeczywisty nagłówek CSP (nie Report-Only)
CSP_REPORT_ONLY = False

# X-Content-Type-Options - Zapobiega MIME type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# X-Frame-Options - Zapobiega clickjacking (już mamy middleware)
X_FRAME_OPTIONS = 'DENY'

# X-XSS-Protection - Wyłącza XSS protection w przeglądarce (CSP jest lepszy)
SECURE_BROWSER_XSS_FILTER = False