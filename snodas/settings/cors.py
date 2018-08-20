# Settings for CORS - Cross-Origin Resource Sharing
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
# https://github.com/ottoyiu/django-cors-headers

INSTALLED_APPS += ('corsheaders', )

CORS_ORIGIN_WHITELIST = (
    'ebagis.geog.pdx.edu',
    'test.ebagis.geog.pdx.edu',
    'localhost:8000',
    'localhost:8080',
    'localhost:3000',
)

# we allow access to everything
CORS_URLS_REGEX = r'.*'

# we can also allow cookies, but this is a security risk
# and doesn't seem to be necessary
#CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE = ('corsheaders.middleware.CorsMiddleware', ) + MIDDLEWARE
