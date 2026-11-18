"""
Configuración del proyecto ERP (core/settings.py).
Django 4.2 - funciona en local (Windows) y en Render.
"""
import os
import sys
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Seguridad básica
# ---------------------------------------------------------------------------
# En Render define SECRET_KEY y DEBUG=False como variables de entorno.
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-cambia-esto-solo-para-desarrollo-local',
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('1', 'true', 'yes')

# True cuando se ejecuta "python manage.py test"
TESTING = 'test' in sys.argv

# ---------------------------------------------------------------------------
# Hosts permitidos
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'salinas-msr01.onrender.com']

# Render define esta variable automáticamente con tu dominio .onrender.com
RENDER_HOST = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)

# Hosts extra opcionales: ALLOWED_HOSTS_EXTRA="erp.miempresa.com,otro.com"
_extra_hosts = os.environ.get('ALLOWED_HOSTS_EXTRA', '')
ALLOWED_HOSTS += [h.strip() for h in _extra_hosts.split(',') if h.strip()]

CSRF_TRUSTED_ORIGINS = ['https://salinas-msr01.onrender.com']
if RENDER_HOST:
    _origin = f'https://{RENDER_HOST}'
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)

# Render termina HTTPS en su proxy; esto le dice a Django que la petición es segura
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG and not TESTING:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
# core/settings.py — actualizar INSTALLED_APPS (terceros):
# core/settings.py — actualizar INSTALLED_APPS:
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Terceros
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',              # ← nuevo (nombre de app es django_filters)
    'whitenoise.runserver_nostatic',
    # Apps del 
    # ERP
    'core',
    'clientes',
    'proveedores',
    'productos',
    'ventas',
    'reportes',
    'configuracion',
    'catalogo',                    # ← nuevo
]
# ── DRF ──────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------]

ROOT_URLCONF = 'core.urls'

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
                # Context processor del carrito — W13
                'catalogo.context_processors.carrito_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
# Si existe DATABASE_URL (Render/PostgreSQL) se usa; si no, SQLite local.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# Validación de contraseñas
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True
# ---------------------------------------------------------------------------
# Archivos estáticos y media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # justo debajo de SecurityMiddleware
    # ...el resto
]
SSTORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # justo debajo de SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# En desarrollo y en tests: almacenamiento simple (no exige manifiesto).
# En producción: WhiteNoise con manifiesto (requiere collectstatic en el build).
if TESTING:
    _static_backend = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    _static_backend = 'whitenoise.storage.CompressedStaticFilesStorage'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': _static_backend},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── STRIPE (Pasarela de pago) ──────────────────────────────────────────────
STRIPE_SECRET_KEY      = env('STRIPE_SECRET_KEY',      default='sk_test_placeholder')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='pk_test_placeholder')
STRIPE_WEBHOOK_SECRET  = env('STRIPE_WEBHOOK_SECRET',  default='whsec_placeholder')



# ---------------------------------------------------------------------------
# Jazzmin (tema del admin)
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    'site_title': 'ERP Admin',
    'site_header': 'ERP',
    'site_brand': 'ERP',
    'welcome_sign': 'Bienvenido al ERP',
    'copyright': 'ERP',
    'search_model': ['clientes.Cliente'],
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'theme': 'default',
    # Reemplaza a la clave obsoleta 'dark_mode_theme'
    'default_theme_mode': 'auto',
}

# ── DJANGO SITES (requerido por allauth) ──────────────────────────────────
SITE_ID = 1

# ── AUTHENTICATION BACKENDS ───────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    # Backend estándar de Django (username + password en admin)
    'django.contrib.auth.backends.ModelBackend',
    # Backend de allauth (permite login por email también)
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ── ALLAUTH: configuración para desarrollo académico ──────────────────────
ACCOUNT_LOGIN_METHODS          = {'username'}   # login por username
ACCOUNT_EMAIL_REQUIRED         = False          # no obligar correo
ACCOUNT_EMAIL_VERIFICATION     = 'none'         # no enviar email de verificación
ACCOUNT_LOGOUT_ON_GET          = True           # logout sin confirmar (dev)
ACCOUNT_SESSION_REMEMBER       = True           # recordar sesión

# LOGIN_URL y LOGIN_REDIRECT_URL ya definidos en W01:
# LOGIN_URL           = '/accounts/login/'
# LOGIN_REDIRECT_URL  = '/productos/'
LOGOUT_REDIRECT_URL = '/'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/productos/'
LOGOUT_REDIRECT_URL = '/'

# ── CELERY — Cola de tareas asíncronas ────────────────────────────
CELERY_BROKER_URL        = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = env('REDIS_URL', default='redis://localhost:6379/0')

CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_TIMEZONE = TIME_ZONE   # 'America/Mexico_City'

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_TASK_SOFT_TIME_LIMIT = 300   # 5 minutos
CELERY_TASK_TIME_LIMIT      = 360   # 6 minutos (límite duro)

CELERY_TASK_DEFAULT_QUEUE = 'erp_django'

# Modo eager: ejecuta las tareas en el mismo proceso, sin Redis ni worker.
# Déjalo en False cuando tengas Redis; actívalo en .env (CELERY_EAGER=True)
# solo si no puedes instalar ningún broker.
CELERY_TASK_ALWAYS_EAGER     = env.bool('CELERY_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True
