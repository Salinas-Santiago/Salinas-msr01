"""
Configuración del proyecto ERP (core/settings.py).
Django 4.2 - funciona en local (Windows) y en Render.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

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
INSTALLED_APPS = [
    'jazzmin',  # debe ir ANTES de django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps del ERP
    'clientes',
    'configuracion',
    'productos',
    'reportes',
    'proveedores',
    'ventas',
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # quitar si no usas WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
STATIC_ROOT = BASE_DIR / 'staticfiles'

_static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []

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