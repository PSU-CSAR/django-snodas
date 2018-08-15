from split_settings.tools import optional, include

from ..management.utils import load_conf_file


conf_settings = load_conf_file()

INSTANCE_NAME = conf_settings.get('INSTANCE_NAME')
ENV = conf_settings.get('ENV', 'production')

SECRET_KEY = conf_settings.get('SECRET_KEY')

DATABASE_NAME = conf_settings.get('DATABASE_NAME', INSTANCE_NAME)
DATABASE_USER = conf_settings.get('DATABASE_USER', INSTANCE_NAME)
DATABASE_PASSWORD = conf_settings.get('DATABASE_PASSWORD')
DATABASE_HOST = conf_settings.get('DATABASE_HOST', None)
DATABASE_PORT = conf_settings.get('DATABASE_PORT', None)

SITE_DOMAIN_NAME = conf_settings.get('SITE_DOMAIN_NAME', None)
SUBDOMAINS = conf_settings.get('SUBDOMAINS', [])


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = conf_settings.get('DEBUG', False)


# first pull in the base settings
settings_files = [
    'base.py',
#    'caching.py',
    'database.py',
    'logging.py',
    'cors.py',
]

# add the env-specific settings and any additional settings
#settings_files.append(optional(ENV+'.py'))
settings_files.extend(conf_settings.get('ADDITIONAL_SETTING_FILES', []))

# always use the local settings file if present
settings_files.append(optional('local_settings.py'))

# now load all the settings files
include(*settings_files, scope=globals())
