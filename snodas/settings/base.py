"""
Django settings for snodas project.
"""
from __future__ import absolute_import

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


# Application definition
INSTALLED_APPS = (
    # project
    'snodas',

    # django libs
    'django.contrib.gis',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

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
REST_ROOT = "/"


STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

SITE_STATIC_ROOT = os.path.join(BASE_DIR, 'local_static')
ADMIN_MEDIA_PREFIX = '/static/admin/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIGRATION_MODULES = {
    'sites': 'snodas.fixtures.sites_migrations',
}


# project-wide email settings
EMAIL_SUBJECT_PREFIX = "[snodas] "
DEFAULT_FROM_EMAIL = "ebagis@pdx.edu"
