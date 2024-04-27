"""
Django settings for snodas project.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '[::1]',
    SITE_DOMAIN_NAME,
]

ALLOWED_HOSTS += [f'{sd}.{SITE_DOMAIN_NAME}' for sd in SUBDOMAINS]

# Application definition
INSTALLED_APPS = (
    # project
    'snodas',
    # django libs
    'django.contrib.gis',
)

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {},
    },
]

ROOT_URLCONF = 'snodas.urls'
WSGI_APPLICATION = 'snodas.wsgi.application'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'US/Pacific'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Django user model
AUTH_USER_MODEL = 'auth.User'

## URL PATH SETTINGS
# settings for rest framework
REST_ROOT = ''

MIGRATION_MODULES = {
    'sites': 'snodas.fixtures.sites_migrations',
}

# project-wide email settings
EMAIL_SUBJECT_PREFIX = '[snodas] '
DEFAULT_FROM_EMAIL = 'ebagis@pdx.edu'
