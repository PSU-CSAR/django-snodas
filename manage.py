#!/usr/bin/env python
from __future__ import absolute_import, print_function

import os
import sys
import logging
import datetime
import logging.handlers


logger = logging.getLogger(__name__)
LOG_SIZE = 50 * (10**6)  # about 50 MB
LOG_COUNT = 5
LOG_FILE = os.path.join(os.path.dirname(__file__), 'manage.log')

CONF_FILE = os.path.join(os.path.dirname(__file__), 'project.conf')


def activate_help():
    import yaml
    with open(CONF_FILE) as f:
        instance_name = yaml.load(f)['INSTANCE_NAME']
    return (
        'ERROR: snodas.settings could not be imported.\n'
        'It looks like you need to activate the conda environment '
        'for this instance, which you can do by running '
        '`activate {}`'.format(instance_name)
    )


def install(help=False):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    # first we append the path with the management package
    # so we can import utils in the install module
    sys.path.append(
        os.path.join(
            this_dir,
            'snodas',
            'management',
        )
    )
    # then we add the commands package to the path
    # so we have access to the install module
    sys.path.append(
        os.path.join(
            this_dir,
            'snodas',
            'management',
            'commands',
        )
    )
    # and lastly we add the directory of this file
    # to the path so we can import from setup.py
    sys.path.append(
        os.path.join(
            this_dir,
        )
    )
    from install import Install
    if help:
        Install.print_help(sys.argv[0], sys.argv[2])
    else:
        Install.run_from_argv(sys.argv)


def default_django_command():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "snodas.settings")

    # check to make sure we can import the settings
    # otherwise, we suspect the env has not been activated
    #
    # TODO: this check is almost pointless, as the wrong env could be
    # activated and this would not prevent execution. I should
    # do some sort of more advanced check of the settings to verify that
    # they match the current project.
    try:
        import snodas.settings
    except ImportError:
        logger.debug(
            'snodas.settings couldn\'t be imported; '
            'looks like the correct env is not activated'
        )
        print(activate_help())
        return 1

    # hacky workaround to allow snodas command to use the
    # autoreloader with the runserver and runcelery commands
    # (problem is that the reload uses subprocess to call
    # sys.executable with the sys.argv[0] as its first arg,
    # which means effectively means it calls `python snodas ...`,
    # which fails either because snodas cannot be found, or
    # sondas is found, and it is the snodas package in the
    # current directory.)
    if len(sys.argv) > 1 and \
            sys.argv[1] == 'runserver' and \
            not ('--help' in sys.argv or '-h' in sys.argv):
        logger.debug(
            'rewritting sys.argv[0] from {} to {}'.format(
                sys.argv[0],
                __file__,
            )
        )
        sys.argv[0] = __file__

    from django.core.management import execute_from_command_line
    logger.debug(
        'executing from the command line with sys.argv: {}'.format(sys.argv)
    )
    return execute_from_command_line(sys.argv)


def main():
    manage_log = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=LOG_SIZE,
        backupCount=(LOG_COUNT - 1),
    )
    formatter = logging.Formatter(
        '%(asctime)s %(name)s [%(levelname)-5s] %(message)s'
    )
    manage_log.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(manage_log)
    #logging.basicConfig(
    #    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manage_%s_%d.log' %(datetime.datetime.now().strftime('%y%m%d_%H%M%S'), os.getpid())),
    #    filemode='w',
    #    format='%(asctime)s [%(levelname)-5s] %(message)s',
    #    level=logging.DEBUG,
    #)

    if len(sys.argv) > 1 and sys.argv[1] == 'install':
        logger.debug('install command run')
        return install()
    if len(sys.argv) > 1 and \
            os.path.basename(sys.argv[0]) == 'manage.py' and \
            sys.argv[1] == 'help' and \
            sys.argv[2] == 'install':
        logger.debug('install help run')
        return install(help=True)
    elif not os.path.isfile(CONF_FILE):
        logger.error('config file could not be loaded: {}'.format(CONF_FILE))
        print('ERROR: Could not find configuration file {}.'.format(CONF_FILE))
        print('Has this instance been installed? '
              'Try running `python manage.py install`.')
    else:
        try:
            return default_django_command()
        except Exception as e:
            logger.exception(e)
            raise
            # before I was returning -1, but I don't know why anymore
            return -1


if __name__ == "__main__":
    sys.exit(main())
