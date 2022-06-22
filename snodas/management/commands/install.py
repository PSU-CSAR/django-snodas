from __future__ import print_function, absolute_import

import os
import sys
import yaml
import argparse
import subprocess
import warnings

from getpass import getpass

try:
    from django.core.management.base import (
        BaseCommand, CommandError, CommandParser
    )
except ImportError:
    BaseCommand = object

# if we are calling this from the install command in snodas.py,
# this import will fail with the error "attempted a relative
# import in a non-package" because we will have imported the
# install module directly, without the snodas package being
# loaded, so we add the utils to the path in snodas.py and
# import that module here directly.
try:
    from .. import utils
except ValueError:
    import utils
except ImportError:
    import utils


if sys.version_info[0] == 2:
    iteritems = dict.iteritems
    input = raw_input
else:
    iteritems = dict.items


class remove_const(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(remove_const, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = argparse._copy.copy(
            argparse._ensure_value(namespace, self.dest, [])
        )
        try:
            items.remove(self.const)
        except ValueError:
            pass
        else:
            setattr(namespace, self.dest, items)


class InstallError(Exception):
    pass


def get_password(prompt):
    while True:
        first = getpass(prompt)
        second = getpass('Enter again to confirm: ')
        if first == second:
            break
        print('Whoops, those don\'t match. Try again.\n')
    return first


# this class is a "pseudo-command": it is structured similarly
# to a django managment command, and borrows some portions of
# django.core.management.Command for familiarity. However, it
# has some differences, as it is intended to be run without
# django installed via a special version of manage.py (in this
# project as snodas.py).
class Install(object):
    help = "Install this snodas instance to the local system."

    def __init__(self):
        pass

    def default_conf_file(self):
        return os.path.join(utils.get_project_root(), utils.CONF_FILE_NAME)

    def get_version(self):
        from setup import get_version as gv
        return gv()

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
        parser = argparse.ArgumentParser(
            prog="{} {}".format(os.path.basename(prog_name), subcommand),
            description=self.help,
        )
        self.add_arguments(parser)
        return parser

    @classmethod
    def add_arguments(cls, parser):
        # base options
        parser.add_argument(
            '--version',
            action='store_true',
            help='Display the version of snodas to be installed then exit.',
        )
        parser.add_argument(
            '-v',
            '--verbosity',
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help=('Verbosity level; 0=minimal output, 1=normal output, '
                  '2=verbose output, 3=very verbose output'),
        )

        # config options
        parser.add_argument(
            '--no-configure',
            action='store_true',
            help=('Don\'t write the config file. '
                  'Will error if no config is present. '
                  'Use this to reinstall the instance '
                  'using an existing config.'),
        )
        parser.add_argument(
            '--overwrite-conf',
            action='store_true',
            help=('Overwrite an existing conf file. '
                  'Default behavior is to fail with an error '
                  'if a conf file already exists.'),
        )
        parser.add_argument(
            '-n',
            '--instance-name',
            help=('The name of the snodas instance. '
                  'Default the name of the directory '
                  'containing this django-snodas instance.'),
        )
        parser.add_argument(
            '--domain-name',
            help=('The domain name of this snodas instance. '
                  'Default is to prompt for user input.'),
        )
        parser.add_argument(
            '-N',
            '--db-name',
            help='The name of the database. Default is the instance name.',
        )
        parser.add_argument(
            '-u',
            '--db-user',
            help='The name of the DB user. Default is the instance name.',
        )
        parser.add_argument(
            '-p',
            '--db-password',
            help=('Password for the specified DB user. '
                  'Default is to prompt user for input.'),
        )
        parser.add_argument(
            '--db-host',
            help=('Hostname of the DB server. '
                  'Default is None, which means localhost.'),
        )
        parser.add_argument(
            '--db-port',
            help=('Port for the DB server. '
                  'Default is None, which will use postgres default.'),
        )
        parser.add_argument(
            '-k',
            '--secret-key',
            help=('A django-style secret key. '
                  'Default is to generate a random string of chars.'),
        )
        parser.add_argument(
            '-l',
            '--secret-key-length',
            type=int,
            default=50,
            help=('The number of chars if generating a secret key. '
                  'Default is 50 chars.'),
        )
        parser.add_argument(
            '-e',
            '--env',
            help=('The environment name. '
                  'Should match an env-specific settings module. '
                  'Default is to inspect instance path and extract.'),
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help=('Enable debug mode. '
                  'Default is disabled unless ENV is development. '
                  'DO NOT use debug in production.'),
        )
        parser.add_argument(
            '-a',
            '--additional-settings-file',
            action='append',
            help=('The name of an addtional settings file to use.'),
        )
        parser.add_argument(
            '-o',
            '--output-file',
            help=('Where to output settings file. '
                  'Default is a file named "project.conf" '
                  'in the instance root.'),
        )

        # env options
        parser.add_argument(
            '--conda',
            default='conda',
            help=('The conda executable to use to make the environment. '
                  'Default is to use whatever conda is on the path.'),
        )
        parser.add_argument(
            '--no-env',
            dest='make_env',
            action='store_false',
            help=('Don\'t make a conda env, '
                  'just intall to the current python. '
                  'Default is to make a new conda env.'),
        )
        parser.add_argument(
            '--no-conda-deps',
            dest='install_conda_req',
            action='store_false',
            help=('Don\'t use conda to install dependencies '
                  'from conda-requirements. '
                  'Default is to install all dependencies.'),
        )
        parser.add_argument(
            '--conda-requirements',
            default='conda-requirements.txt',
            help=('File listing packages to install with conda. '
                  'Default is conda-requirements.txt'),
        )
        parser.add_argument(
            '--python-version',
            help=('Python version to install. Use setuptools version '
                  'specification, e.g., ==2.7.11 or >=2.7.8. '
                  'Default is to get version designated in setup.py'),
        )
        parser.add_argument(
            '-F',
            '--force',
            action='store_true',
            help=('Force creation of conda env '
                  '(removing a previously existing '
                  'environment of the same name).'
                  'Default is to error if an env '
                  'already exists of the same name.'),
        )

        # install options
        parser.add_argument(
            '-d',
            '--dev',
            dest='install_options',
            action='append_const',
            const='dev',
            help=('Include development packages with installation. '
                  'Default is false, unless env is development, '
                  'in which case this option cannot be disabled.'),
        )

    @classmethod
    def run_from_argv(cls, argv):
        self = cls()
        self._called_from_command_line = True
        parser = self.create_parser(argv[0], argv[1])

        options = parser.parse_args(argv[2:])
        cmd_options = vars(options)
        # Move positional args out of options to mimic legacy optparse
        args = cmd_options.pop('args', ())

        self.execute(*args, **cmd_options)

    @classmethod
    def print_help(cls, prog_name, subcommand):
        """
        Print the help message for this command, derived from
        ``self.usage()``.
        """
        install = cls()
        parser = install.create_parser(prog_name, subcommand)
        parser.print_help()

    def extract_settings_from_options(self, options):
        settings = {}

        settings['ENV'] = options.get('env') or utils.get_env_name()

        if not settings['ENV']:
            raise InstallError(
                'Could not extract env name from path and none specified.'
            )

        pyfile = settings['ENV'] + '.py'
        if not os.path.isfile(utils.get_settings_file(pyfile)):
            warnings.warn(
                'Could not find settings file for env named {}'
                .format(pyfile),
            )

        settings['DEBUG'] = (
            settings['ENV'] == 'development' or options.get('DEBUG')
        )

        settings['INSTANCE_NAME'] = utils.get_default(
            options,
            'instance_name',
            utils.get_instance_name(),
        )

        if not settings['INSTANCE_NAME']:
            raise InstallError(
                'Could not extract instance name from path and none specified.'
             )

        settings['SECRET_KEY'] = utils.get_default(
            options,
            'secret_key',
            utils.generate_secret_key(options.get('secret_key_length'))
        )

        settings['DATABASE_NAME'] = utils.get_default(
            options,
            'db_name',
            settings['INSTANCE_NAME'],
        )
        settings['DATABASE_USER'] = utils.get_default(
            options,
            'db_user',
            settings['DATABASE_NAME'],
        )
        settings['DATABASE_PASSWORD'] = utils.get_default(
            options,
            'db_password',
            get_password('Please enter the database user password: '),
        )
        settings['DATABASE_HOST'] = utils.get_default(options, 'db_host', None)
        settings['DATABASE_PORT'] = utils.get_default(options, 'db_port', None)


        settings['SITE_DOMAIN_NAME'] = utils.get_default(
            options,
            'domain',
            input('Enter in the domain name for this project instance: '),
        )
        settings['SUBDOMAINS'] = []

        settings['ADDITIONAL_SETTINGS_FILES'] = utils.get_default(
            options,
            'additional_settings_file',
            [],
        )

        return settings

    def write_conf_file(self):
        with open(self.output_file, 'w') as f:
            f.write('# This file contains SECRET information!\n')
            f.write('# Keep the contents of the file private,\n')
            f.write('# especially for production instances.\n')
            f.write('# DO NOT commit this file.\n\n')
            yaml.dump(self.settings, f, default_flow_style=False)

        self.vprint(
            2,
            'Wrote project conf to config file {}'.format(self.output_file)
        )

    def create_conda_env(self, options):
        import json

        # if we've gotten here then this class should have
        # been called from the snodas manage.py, which has
        # added the root project directory to the path,
        # and setup.py should be importable
        from setup import PYTHON_REQUIREMENTS

        conda = options.get('conda')

        conda_info = json.loads(
                subprocess.check_output([conda, 'info', '--json'])
            )

        name = self.settings['INSTANCE_NAME']

        # build the env create command
        install_cmd = [
            conda, 'create', '-y', '-n', name,
            'python{}'.format(PYTHON_REQUIREMENTS),
        ]

        if options.get('force'):
            install_cmd.append('--force')

        if options.get('install_conda_req'):
            install_cmd.extend(['--file', options.get('conda_requirements')])

        # if force isn't set to replace an existing env,
        # then we want to check for the env and fail if exists
        if not options.get('force'):
            if name in \
                    [os.path.basename(env) for env in conda_info['envs']]:
                raise InstallError(
                    'A conda env of name '
                    '{} already exists.'.format(name)
                )

        self.vprint(
            2,
            'creating conda env with the following command:'
            '{}'.format(install_cmd)
        )

        # now we create the env
        self.vprint(3, subprocess.check_output(install_cmd))
        self.env_root = os.path.join(conda_info['sys.prefix'], 'envs', name)

        self.vprint(1, 'conda env created at {}'.format(self.env_root))

    def install(self, options):
        pip = self.get_pip()

        install_options = options.get('install_options') or []

        if self.settings['ENV'] == 'development' and \
                'dev' not in install_options:
            install_options.append('dev')

        install_options = \
            '[{}]'.format(','.join(
                [opt for opt in install_options if opt]
            )) if install_options else ''

        cmd = [
            pip, 'install', '-e',
            '{}{}'.format(utils.get_project_root(), install_options),
        ]

        self.vprint(
            2,
            'Processing the following command for install:\n'
            '{}'.format(cmd)
        )

        self.vprint(3, subprocess.check_output(cmd))

    def get_pip(self):
        if hasattr(self, 'env_root'):
            return os.path.join(self.env_root, 'Scripts', 'pip.exe')
        else:
            return 'pip'

    def print_conf(self):
        if self.verbosity < 2:
            return
        print('Using the following configuration settings:')
        for key, val in sorted(iteritems(self.settings)):
            print("    {} = {}".format(key, val))

    def vprint(self, level, *args, **kwargs):
        if self.verbosity >= level:
            print(*args, **kwargs)

    def snodas_command_error(self):
        project_root = utils.get_project_root()
        project_root_message = ''
        if project_root != os.getcwd():
            project_root_message = \
                ' from the project\'s root directory {}'.format(project_root)

        print(
            ('Unfortunately, the install command must be run '
             'using the project\'s manage.py script instead of '
             'the snodas command. Try running `python manage.py install`{}.'
             ).format(project_root_message)
        )

    def execute(self, *args, **options):
        if os.path.basename(sys.argv[0]) == 'snodas':
            self.snodas_command_error()
            return 1

        if options.get('version'):
            print('snodas version {}'.format(self.get_version()))
            return 2

        self.verbosity = options.get('verbosity')

        self.output_file = utils.get_default(
            options,
            'output_file',
            self.default_conf_file(),
        )

        self.vprint(2, 'Config file path will be {}'.format(self.output_file))

        conf_exists = os.path.isfile(self.output_file)

        if options.get('no_configure') and conf_exists:
            self.vprint(1,'Reusing existing configuration from {}'.format(self.output_file))
            self.settings = utils.load_conf_file(self.output_file)
        elif options.get('no_configure') and not conf_exists:
            print('ERROR: no-configure option specified '
                  'but configuration file does not exist.')
            return 3
        elif conf_exists and not options.get('overwrite_conf'):
            print('ERROR: configuration file already exists '
                  'and overwrite-conf option not specified.')
            return 4
        else:
            self.vprint(1, 'Generating configuration from install options')
            self.settings = self.extract_settings_from_options(options)

        self.print_conf()

        if options.get('make_env'):
            self.vprint(1, 'creating conda env')
            self.create_conda_env(options)
        else:
            self.vprint(
                1,
                'conda env creation skipped; '
                'installing to active python instance',
            )

        self.vprint(1, 'Installing project')
        self.install(options)

        if not options.get('no_configure'):
            self.write_conf_file()

        # print next steps for user
        self.vprint(1, '\nInstallation successful!')
        self.vprint(
            1,
            ('\nNext, activate the new conda env for the project:\n\n'
             '`activate {}`\n\n'
             '(`source` is required in a sh-like shell).\n\n'
             'Then, setup any required services for this instance:\n\n:'
             '`snodas createdb [options]  # creates a postgres DB`\n'
             '`snodas setupiis [options]  # creates a site in IIS`\n\n'
             'Once the services are configured, '
             'you can run a webserver or celery:\n\n'
             '`snodas runserver [options]'
             'To learn what options apply to each command, try:\n\n'
             '`snodas help <command>`'
             ).format(self.settings['INSTANCE_NAME'])
        )


# Unlike the Install class above, this is actually a django command.
# It uses parts of the Install class to provide a way to integrate
# the install command into the manage.py command display, for the
# sake of a consistent user experience/documentation. It is never
# intended to be executed, and it will raise an error if attempted.
class Command(BaseCommand):
    help = Install.help

    requires_system_checks = False

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command. We use the default definition
        from the django source, but we drop all the options because we
        don't want to display options that are not supported.
        """
        parser = CommandParser(
            self, prog="%s %s" % (os.path.basename(prog_name), subcommand),
            description=Install.help or None,
        )
        self.add_arguments(parser)
        return parser

    def add_arguments(self, parser):
        Install.add_arguments(parser)

    def print_help(self, prog_name, subcommand):
        """
        Print the help message for this command, derived from
        ``self.usage()``.
        """
        if prog_name == 'snodas':
            prog_name = 'manage.py'
            print(
                '\n**PLEASE NOTE: the install command must be run '
                'using the project\'s manage.py script instead of '
                'the snodas command.**\n')
        super(Command, self).print_help(prog_name, subcommand)

    def handle(self, *args, **options):
        raise CommandError(
            'If you got here then you are not running the snodas '
            'manage.py script for your commands. Do not call '
            'install from django-admin.'
        )
