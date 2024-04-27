# os.environ['POSTGIS_GDAL_ENABLED_DRIVERS'] = 'ENABLE_ALL'

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': DATABASE_PASSWORD,
        'HOST': DATABASE_HOST,
        'PORT': DATABASE_PORT,
        'INIT_COMMANDS': [
            'SET ROLE app',
        ],
    },
}
