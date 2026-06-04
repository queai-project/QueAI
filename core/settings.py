"""
QueAI kernel — Django settings.

Defaults seguros: DEBUG=False y SECRET_KEY auto-generada por sesión si no se
provee. Activa modo dev poniendo `DEBUG=True` en el `.env`.
"""

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent

# --- Plugins discovery ---------------------------------------------------
PLUGINS_DIR = BASE_DIR / os.getenv("PLUGINS_DIR", "plugins")
if not PLUGINS_DIR.exists():
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

QUEAI_VERSION = os.getenv("VERSION", "").strip()

# --- Core security -------------------------------------------------------
DEBUG = _env_bool("DEBUG", default=False)

_secret = os.getenv("SECRET_KEY", "").strip()
if not _secret:
    # En producción esto es un error fatal salvo que el operador haya
    # decidido conscientemente correr en modo dev (DEBUG=True).
    if not DEBUG:
        raise RuntimeError(
            "SECRET_KEY no está definida. Genera una con:\n"
            "  python -c \"import secrets; print(secrets.token_urlsafe(50))\"\n"
            "y guárdala en el .env (clave SECRET_KEY=...) antes de arrancar."
        )
    _secret = secrets.token_urlsafe(50)
    logger.warning(
        "DEBUG=True y SECRET_KEY ausente: usando una clave efímera para esta sesión. "
        "Los logins se invalidan al reiniciar."
    )
SECRET_KEY = _secret

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,*")
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:8080")

# --- API REST token --------------------------------------------------------
# El kernel expone /api/v1/ autenticado con un bearer token único.
# - Si QUEAI_API_TOKEN está en .env, se usa tal cual.
# - Si está vacío y DEBUG=True, se autogenera por sesión (logueado).
# - Si está vacío y DEBUG=False, el kernel se niega a arrancar.
_api_token = os.getenv("QUEAI_API_TOKEN", "").strip()
if not _api_token:
    if not DEBUG:
        raise RuntimeError(
            "QUEAI_API_TOKEN no está definido. Genera uno con:\n"
            "  python -c \"import secrets; print(secrets.token_urlsafe(40))\"\n"
            "y guárdalo en el .env antes de arrancar."
        )
    _api_token = secrets.token_urlsafe(40)
    logger.warning(
        "DEBUG=True y QUEAI_API_TOKEN ausente: usando un token efímero para esta "
        "sesión. Mira el valor desde Mi cuenta o regenera. Token: %s",
        _api_token,
    )
QUEAI_API_TOKEN = _api_token

# --- Internal Traefik URL --------------------------------------------------
# El kernel consulta los healthchecks de los plugins por aquí. Como ambos
# están en `queai_network`, el service name `traefik` resuelve al router.
# Override si tu setup usa otro nombre.
QUEAI_INTERNAL_TRAEFIK_URL = os.getenv("QUEAI_INTERNAL_TRAEFIK_URL", "http://traefik").rstrip("/")

# --- Healthcheck por plugin ------------------------------------------------
QUEAI_HEALTHCHECK_TIMEOUT = float(os.getenv("QUEAI_HEALTHCHECK_TIMEOUT", "3"))
QUEAI_HEALTHCHECK_CACHE_TTL = int(os.getenv("QUEAI_HEALTHCHECK_CACHE_TTL", "5"))
# Grace period tras install/start/save_env durante el cual una respuesta
# fallida del healthcheck se reporta como "starting" en vez de "down".
QUEAI_STARTING_GRACE_SECONDS = int(os.getenv("QUEAI_STARTING_GRACE_SECONDS", "60"))

# --- Audit log -------------------------------------------------------------
# Cuando AuditEvent.objects.count() supera MAX_EVENTS, se borran los
# (MAX_EVENTS - KEEP_AFTER_PURGE) más viejos para volver al techo.
QUEAI_AUDIT_MAX_EVENTS = int(os.getenv("QUEAI_AUDIT_MAX_EVENTS", "5000"))
QUEAI_AUDIT_KEEP_AFTER_PURGE = int(os.getenv("QUEAI_AUDIT_KEEP_AFTER_PURGE", "4000"))

# Endurecimiento extra cuando DEBUG=False (producción / self-host).
if not DEBUG:
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "SAMEORIGIN"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "module_manager",
    "system_monitor",
    "marketplace",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["marketplace", "module_manager", "system_monitor", "core/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.queai",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Auth flow -----------------------------------------------------------
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/manager/"
LOGOUT_REDIRECT_URL = "/login/"


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- Static files (whitenoise) ------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# --- Cache ---------------------------------------------------------------
# In-memory por proceso. Suficiente para cachear el resultado de get_apps;
# con gunicorn multi-worker, cada worker tiene su copia (aceptable porque
# el TTL es corto y el coste de fallar el cache es solo un docker compose top).
# FileBasedCache (no LocMem) para que los flags como "queai:starting:<folder>"
# y los cache lookups de get_apps se vean entre workers de gunicorn. Con
# LocMemCache cada worker tiene su propio cache y el feedback "iniciando…"
# no aparecía porque el worker que recibía el healthcheck no era el mismo
# que había recibido el install/start.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/tmp/queai-cache",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    }
}


# --- Logging -------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname:8s} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
