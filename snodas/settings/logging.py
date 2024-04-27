import os

# logging settings
MAX_LENGTH = 5 * 1024 * 1024  # 50 MB
MAX_FILES = 10


# TODO: this is a problem if I just want to import the MANAGE_LOGGING config
# for manage.py. I need to ensure that imports without any dependency problems
# and any name errors in this file are an issue.
#
# I could import setings as a whole and that would resolve the name, but
# manage is already too slow. Importing settings twice seems crazy.
LOG_DIR = os.path.join(BASE_DIR, 'log')


_VERBOSE_FORMATTER = {
    'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
    'datefmt': '%d/%b/%Y %H:%M:%S',
}


def _rotating_file_handler(
    log_name,
    log_level='DEBUG',
    formatter='verbose',
    maxBytes=MAX_LENGTH,
    backupCount=(MAX_FILES - 1),
):
    return {
        'level': log_level,
        'class': 'snodas.utils.logging.RotatingFileHandler',
        'filename': os.path.join(LOG_DIR, log_name),
        'formatter': formatter,
        'maxBytes': MAX_LENGTH,
        'backupCount': (MAX_FILES - 1),
        'makedirs': True,
    }


MANAGE_LOGGING = {
    'formatters': {
        'verbose': _VERBOSE_FORMATTER,
    },
    'handlers': {
        'file': _rotating_file_handler('manage.log'),
    },
    'loggers': {
        'manage': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    },
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': _VERBOSE_FORMATTER,
        'simple': {
            'format': '%(asctime)s %(name)s [%(levelname)s] %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S',
        },
    },
    'handlers': {
        'file': _rotating_file_handler('django.log'),
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'DEBUG',
        },
    },
}
