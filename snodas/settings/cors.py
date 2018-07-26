# Settings for CORS - Cross-Origin Resource Sharing
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
# https://github.com/ottoyiu/django-cors-headers

INSTALLED_APPS += ('corsheaders', )

CORS_ORIGIN_ALLOW_ALL = True

CORS_ORIGIN_WHITELIST = (
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'null',
)

# we allow access to everything
CORS_URLS_REGEX = r'.*'

# we can also allow cookies, but this is a security risk
# and doesn't seem to be necessary
#CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE = ('corsheaders.middleware.CorsMiddleware', ) + MIDDLEWARE
