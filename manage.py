#!/usr/bin/env python
import logging
import logging.handlers
import os
import sys

from pathlib import Path

logger = logging.getLogger(__name__)
LOG_SIZE = 50 * (10**6)  # about 50 MB
LOG_COUNT = 5

THIS = Path(__file__).resolve()
THIS_DIR = THIS.parent
LOG_FILE = THIS_DIR / 'manage.log'
CONF_FILE = THIS_DIR / 'project.conf'


ACTIVATE_HELP: str = (
    'ERROR: snodas.settings could not be imported.\n'
    'It looks like you need to activate the proper conda/virtual environment.'
)


def install(help=False):
    # first we append the path with the management package
    # so we can import utils in the install module
    sys.path.append(str(THIS_DIR / 'snodas' / 'management'))

    # then we add the commands package to the path
    # so we have access to the install module
    sys.path.append(str(THIS_DIR / 'snodas' / 'management' / 'commands'))

    # and lastly we add the directory of this file
    # to the path so we can import from setup.py
    sys.path.append(str(THIS_DIR))

    from install import Install  # type: ignore

    if help:
        Install.print_help(sys.argv[0], sys.argv[2])
    else:
        Install.run_from_argv(sys.argv)


def default_django_command():
    from importlib.util import find_spec

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snodas.settings')

    # check to make sure we can import the settings
    # otherwise, we suspect the env has not been activated
    #
    # TODO: this check is almost pointless, as the wrong env could be
    # activated and this would not prevent execution. I should
    # do some sort of more advanced check of the settings to verify that
    # they match the current project.
    if find_spec('snodas.settings') is None:
        logger.debug(
            "snodas.settings couldn't be imported; "
            'looks like the correct env is not activated',
        )
        print(ACTIVATE_HELP)  # noqa: T201
        return 1

    # hacky workaround to allow snodas command to use the
    # autoreloader with the runserver and runcelery commands
    # (problem is that the reload uses subprocess to call
    # sys.executable with the sys.argv[0] as its first arg,
    # which means effectively means it calls `python snodas ...`,
    # which fails either because snodas cannot be found, or
    # sondas is found, and it is the snodas package in the
    # current directory.)
    if (
        len(sys.argv) > 1
        and sys.argv[1] == 'runserver'
        and not ('--help' in sys.argv or '-h' in sys.argv)
    ):
        logger.debug(
            'rewritting sys.argv[0] from %s to %s',
            sys.argv[0],
            __file__,
        )
        sys.argv[0] = __file__

    from django.core.management import execute_from_command_line  # type: ignore

    logger.debug(
        'executing from the command line with sys.argv: %s',
        sys.argv,
    )
    return execute_from_command_line(sys.argv)


def main():
    manage_log = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=LOG_SIZE,
        backupCount=(LOG_COUNT - 1),
    )
    formatter = logging.Formatter(
        '%(asctime)s %(name)s [%(levelname)-5s] %(message)s',
    )
    manage_log.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(manage_log)

    if len(sys.argv) > 1 and sys.argv[1] == 'install':
        logger.debug('install command run')
        return install()

    if (
        len(sys.argv) > 1
        and Path(sys.argv[0]).name == 'manage.py'
        and sys.argv[1] == 'help'
        and sys.argv[2] == 'install'
    ):
        logger.debug('install help run')
        return install(help=True)

    if not CONF_FILE.is_file():
        logger.error('config file could not be loaded: %s', CONF_FILE)
        print(f'ERROR: Could not find configuration file {CONF_FILE}.')  # noqa: T201
        print(  # noqa: T201
            'Has this instance been installed? '
            'Try running `python manage.py install`.',
        )
        return None

    try:
        return default_django_command()
    except Exception:
        logger.exception('Failure running CLI')
        raise


if __name__ == '__main__':
    sys.exit(main())
