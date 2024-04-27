import argparse
import os
import subprocess
import sys
import warnings
from getpass import getpass

import yaml

try:
    from django.core.management.base import BaseCommand, CommandError, CommandParser
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


def is_development(settings):
    return settings['DEPLOYMENT_TYPE'] == 'development'


class InstallError(Exception):
    pass


def get_password(prompt):
    while True:
        first = getpass(prompt)
        second = getpass('Enter again to confirm: ')
        if first == second:
            break
        print("Whoops, those don't match. Try again.\n")
    return first


# this class is a "pseudo-command": it is structured similarly
# to a django managment command, and borrows some portions of
# django.core.management.Command for familiarity. However, it
# has some differences, as it is intended to be run without
# django installed via a special version of manage.py (in this
# project as snodas.py).
class Install:
    help = 'Install this snodas project instance to the local system.'

    def __init__(self):
        pass

    def default_conf_file(self):
        return os.path.join(utils.get_project_root(), utils.CONF_FILE_NAME)

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
        parser = argparse.ArgumentParser(
            prog=f'{os.path.basename(prog_name)} {subcommand}',
            description=self.help,
        )
        self.add_arguments(parser)
        return parser

    @classmethod
    def add_arguments(cls, parser):
        # base options
        parser.add_argument(
            '-v',
            '--verbosity',
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help=(
                'Verbosity level; 0=minimal output, 1=normal output, '
                '2=verbose output, 3=very verbose output'
            ),
        )

        # config options
        parser.add_argument(
            '--no-configure',
            action='store_true',
            help=(
                "Don't write the config file. "
                'Will error if no config is present. '
                'Use this to reinstall the instance '
                'using an existing config.'
            ),
        )
        parser.add_argument(
            '--overwrite-conf',
            action='store_true',
            help=(
                'Overwrite an existing conf file. '
                'Default behavior is to fail with an error '
                'if a conf file already exists.'
            ),
        )
        parser.add_argument(
            '-n',
            '--project-name',
            required=True,
            help=('The name of the snodas project instance.'),
        )
        parser.add_argument(
            '-d',
            '--domain-name',
            required=True,
            help=('The domain name of this snodas project instance.'),
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
            help=(
                'Password for the specified DB user. '
                'Default is to prompt user for input.'
            ),
        )
        parser.add_argument(
            '--db-host',
            help=(
                'Hostname of the DB server. ' 'Default is None, which means localhost.'
            ),
        )
        parser.add_argument(
            '--db-port',
            help=(
                'Port for the DB server. '
                'Default is None, which will use postgres default.'
            ),
        )
        parser.add_argument(
            '-k',
            '--secret-key',
            help=(
                'A django-style secret key. '
                'Default is to generate a random string of chars.'
            ),
        )
        parser.add_argument(
            '-l',
            '--secret-key-length',
            type=int,
            default=50,
            help=(
                'The number of chars if generating a secret key. '
                'Default is 50 chars.'
            ),
        )
        parser.add_argument(
            '-t',
            '--deployment-type',
            choices=['development', 'testing', 'production'],
            required=True,
            help=(
                'The deployment type. '
                'Should match an deployment-specific settings module.'
            ),
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help=(
                'Enable debug mode. '
                'Default is disabled unless deployment type is development. '
                'DO NOT use debug in production.'
            ),
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
            help=(
                'Where to output settings file. '
                'Default is a file named "project.conf" '
                'in the instance root.'
            ),
        )

        # env options
        parser.add_argument(
            '--conda',
            default='conda',
            help=(
                'The conda executable to use to make the environment. '
                'Default is to use whatever conda is on the path.'
            ),
        )
        parser.add_argument(
            '--env-name',
            help='The name of the conda env. Default is the instance name.',
        )
        parser.add_argument(
            '--no-env',
            dest='make_env',
            action='store_false',
            help=(
                "Don't make a conda env, "
                'just install to the current python. '
                'Default is to make a new conda env.'
            ),
        )
        parser.add_argument(
            '--no-conda-deps',
            dest='install_conda_req',
            action='store_false',
            help=(
                "Don't use conda to install dependencies "
                'from conda-requirements. '
                'Default is to install all dependencies.'
            ),
        )
        parser.add_argument(
            '--conda-requirements',
            default='conda-requirements.txt',
            help=(
                'File listing packages to install with conda. '
                'Default is conda-requirements.txt'
            ),
        )
        parser.add_argument(
            '--python-version',
            help=(
                'Python version to install. Use setuptools version '
                'specification, e.g., ==2.7.11 or >=2.7.8. '
                'Default is to get version designated in setup.py'
            ),
        )
        parser.add_argument(
            '--overwrite-env',
            action='store_true',
            help=(
                'Force creation of conda env '
                '(removing a previously existing '
                'environment of the same name).'
                'Default is to error if an env '
                'already exists of the same name.'
            ),
        )

    @classmethod
    def run_from_argv(cls, argv):
        self = cls()
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

        settings['DEPLOYMENT_TYPE'] = options.get('deployment_type')

        pyfile = settings['DEPLOYMENT_TYPE'] + '.py'
        if not os.path.isfile(utils.get_settings_file(pyfile)):
            warnings.warn(
                f'Could not find settings file for env named {pyfile}',
            )

        settings['DEBUG'] = is_development(settings) or options.get('debug')

        settings['PROJECT_NAME'] = options['project_name']

        settings['SECRET_KEY'] = utils.get_default(
            options,
            'secret_key',
            utils.generate_secret_key(options.get('secret_key_length')),
        )

        settings['DATABASE_NAME'] = utils.get_default(
            options,
            'db_name',
            settings['PROJECT_NAME'],
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

        settings['SITE_DOMAIN_NAME'] = options['domain_name']
        settings['SUBDOMAINS'] = []

        settings['ADDITIONAL_SETTINGS_FILES'] = utils.get_default(
            options,
            'additional_settings_file',
            [],
        )

        settings['CONDA_ENV_NAME'] = utils.get_default(
            options,
            'env_name',
            settings['PROJECT_NAME'],
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
            f'Wrote project conf to config file {self.output_file}',
        )

    @staticmethod
    def get_python_version() -> str:
        import tomllib
        from pathlib import Path

        pyproject = tomllib.loads(
            (Path(utils.get_project_root()) / 'pyproject.toml').read_text(),
        )
        return pyproject['project']['requires-python']

    def create_conda_env(self, options):
        import json

        PYTHON_REQUIREMENTS = self.get_python_version()

        conda = options.get('conda')

        conda_info = json.loads(
            subprocess.run(
                [conda, 'info', '--json'],
                check=True,
                capture_output=True,
            ).stdout,
        )

        name = self.settings['CONDA_ENV_NAME']

        # build the env create command
        install_cmd = [
            conda,
            'create',
            '-y',
            '-n',
            name,
            f'python{PYTHON_REQUIREMENTS}',
        ]

        if options.get('overwrite_env'):
            install_cmd.append('--force')

        if options.get('install_conda_req'):
            install_cmd.extend(['--file', options.get('conda_requirements')])

        # if overwrite_env isn't set to replace an existing env,
        # then we want to check for the env and fail if exists
        if not options.get('overwrite_env'):
            if name in [os.path.basename(env) for env in conda_info['envs']]:
                raise InstallError(
                    'A conda env of name ' f'{name} already exists.',
                )

        self.vprint(
            2,
            'creating conda env with the following command:' f'{install_cmd}',
        )

        # now we create the env
        subprocess.run(install_cmd, check=True)
        self.env_root = os.path.join(conda_info['sys.prefix'], 'envs', name)

        self.vprint(1, f'conda env created at {self.env_root}')

    def install(self):
        pip = self.get_pip()

        # install deps
        cmd = [
            pip,
            'install',
            '-r',
            os.path.join(utils.get_project_root(), 'requirements.txt'),
        ]
        self.vprint(
            2,
            'Processing the following command for install:\n' f'{cmd}',
        )
        subprocess.run(cmd, check=True)

        # install app
        cmd = [
            pip,
            'install',
            '-e',
            utils.get_project_root(),
        ]
        self.vprint(
            2,
            'Processing the following command for install:\n' f'{cmd}',
        )
        subprocess.run(cmd, check=True)

    def get_pip(self):
        if hasattr(self, 'env_root'):
            return os.path.join(self.env_root, 'Scripts', 'pip.exe')
        else:
            return 'pip'

    def print_conf(self):
        if self.verbosity and self.verbosity < 2:
            return
        print('Using the following configuration settings:', flush=True)
        for key, val in sorted(self.settings.items()):
            print(f'    {key} = {val}', flush=True)

    def vprint(self, level, *args, **kwargs):
        kwargs['flush'] = True
        if self.verbosity >= level:
            print(*args, **kwargs)

    def snodas_command_error(self):
        project_root = utils.get_project_root()
        project_root_message = ''
        if project_root != os.getcwd():
            project_root_message = f" from the project's root directory {project_root}"

        print(
            (
                'Unfortunately, the install command must be run '
                "using the project's manage.py script instead of "
                f'the snodas command. Try running `python manage.py install`{project_root_message}.'
            ),
            flush=True,
        )

    def execute(self, *args, **options):
        if os.path.basename(sys.argv[0]) == 'snodas':
            self.snodas_command_error()
            return 1

        self.verbosity = options.get('verbosity')

        self.output_file = utils.get_default(
            options,
            'output_file',
            self.default_conf_file(),
        )

        self.vprint(2, f'Config file path will be {self.output_file}')

        conf_exists = os.path.isfile(self.output_file)

        if options.get('no_configure') and conf_exists:
            self.vprint(1, f'Reusing existing configuration from {self.output_file}')
            self.settings = utils.load_conf_file(self.output_file)
        elif options.get('no_configure') and not conf_exists:
            print(
                'ERROR: no-configure option specified '
                'but configuration file does not exist.'
            )
            return 3
        elif conf_exists and not options.get('overwrite_conf'):
            print(
                'ERROR: configuration file already exists '
                'and overwrite-conf option not specified.'
            )
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
                'conda env creation skipped; ' 'installing to active python instance',
            )

        self.vprint(1, 'Installing project')
        self.install()

        if not options.get('no_configure'):
            self.write_conf_file()

        # print next steps for user
        self.vprint(1, '\nInstallation successful!')
        self.vprint(
            1,
            (
                '\nNext, activate the new conda env for the project:\n\n'
                '`conda activate {}`\n\n'
                'Then, setup any required services for this instance:\n\n'
                '`snodas createdb [options]  # creates a postgres DB`\n'
                '`snodas setupiis [options]  # creates a site in IIS`\n\n'
                'Once the services are configured, '
                'you can run a webserver:\n\n'
                '`snodas runserver [options]'
                'To learn what options apply to each command, try:\n\n'
                '`snodas help <command>`'
            ).format(self.settings['PROJECT_NAME']),
        )


# Unlike the Install class above, this is actually a django command.
# It uses parts of the Install class to provide a way to integrate
# the install command into the manage.py command display, for the
# sake of a consistent user experience/documentation. It is never
# intended to be executed, and it will raise an error if attempted.
class Command(BaseCommand):
    help = Install.help

    requires_system_checks = []

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command. We use the default definition
        from the django source, but we drop all the options because we
        don't want to display options that are not supported.
        """
        parser = CommandParser(
            prog='%s %s' % (os.path.basename(prog_name), subcommand),
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
                "using the project's manage.py script instead of "
                'the snodas command.**\n'
            )
        super(Command, self).print_help(prog_name, subcommand)

    def handle(self, *args, **options):
        raise CommandError(
            'If you got here then you are not running the snodas '
            'manage.py script for your commands. Do not call '
            'install from django-admin.',
        )
