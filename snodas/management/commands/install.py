import argparse
import subprocess
import sys
import warnings

from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Self

try:
    from django.core.management.base import (
        BaseCommand,
        CommandError,
        CommandParser,
    )
except ImportError:
    BaseCommand = None

# if we are calling this from the install command in snodas.py,
# this import will fail with the error "attempted a relative
# import in a non-package" because we will have imported the
# install module directly, without the snodas package being
# loaded, so we add the utils to the path in snodas.py and
# import that module here directly.
try:
    from snodas.management import utils
except (ValueError, ImportError):
    import utils  # type: ignore

SECRET_KEY_LENGTH = 50


class InstallError(Exception):
    pass


def get_password(prompt) -> str:
    while True:
        first = getpass(prompt)
        second = getpass('Enter again to confirm: ')
        if first == second:
            break
        print("Whoops, those don't match. Try again.\n")  # noqa: T201
    return first


@dataclass
class Settings:
    DEPLOYMENT_TYPE: str
    DEBUG: bool
    PROJECT_NAME: str
    SECRET_KEY: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    SITE_DOMAIN_NAME: str
    ADDITIONAL_SETTINGS_FILES: list[str]
    CONDA_ENV_NAME: str
    SNODAS_RASTERDB: str
    SUBDOMAINS: list[str]
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int | None = None

    def __post_init__(self: Self) -> None:
        pyfile: str = self.DEPLOYMENT_TYPE + '.py'
        if not utils.get_settings_file(pyfile).is_file():
            warnings.warn(
                f'Could not find settings file for env named {pyfile}',
                stacklevel=1,
            )

    @classmethod
    def from_options(
        cls: type[Self],
        *,
        deployment_type: str,
        project_name: str,
        raster_db: Path,
        db_name: str | None = None,
        db_user: str | None = None,
        db_password: str | None = None,
        db_host: str | None = None,
        db_port: str | None = None,
        domain_name: str,
        additional_settings_file: list[str] | None = None,
        env_name: str | None = None,
        **_,
    ) -> Self:
        return cls(
            DEPLOYMENT_TYPE=deployment_type,
            DEBUG=(deployment_type == 'development'),
            PROJECT_NAME=project_name,
            SECRET_KEY=utils.generate_secret_key(SECRET_KEY_LENGTH),
            DATABASE_NAME=(db_name if db_name else project_name),
            DATABASE_USER=(db_user if db_user else project_name),
            DATABASE_PASSWORD=(
                db_password
                if db_password
                else get_password('Please enter the database user password: ')
            ),
            DATABASE_HOST=db_host,
            DATABASE_PORT=int(db_port) if db_port is not None else None,
            SITE_DOMAIN_NAME=domain_name,
            SUBDOMAINS=[],
            ADDITIONAL_SETTINGS_FILES=(
                additional_settings_file if additional_settings_file else []
            ),
            CONDA_ENV_NAME=(env_name if env_name else project_name),
            SNODAS_RASTERDB=str(raster_db),
        )


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

    def default_conf_file(self) -> Path:
        return utils.CONF_FILE

    def create_parser(self, prog_name: str, subcommand: str) -> argparse.ArgumentParser:
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
        parser = argparse.ArgumentParser(
            prog=f'{Path(prog_name).name} {subcommand}',
            description=self.help,
        )
        self.add_arguments(parser)
        return parser

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser) -> None:
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
            help=('Hostname of the DB server. Default is None, which means localhost.'),
        )
        parser.add_argument(
            '--db-port',
            help=(
                'Port for the DB server. '
                'Default is None, which will use postgres default.'
            ),
        )
        parser.add_argument(
            '--raster-db',
            required=True,
            type=Path,
            help=(
                'Path of the directory containing (or to contain) '
                'the raster database. New raster databases can be '
                'initialized with the `createrasterdb` command.'
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
            '-a',
            '--additional-settings-file',
            action='append',
            help=('The name of an addtional settings file to use.'),
        )
        parser.add_argument(
            '-o',
            '--output-file',
            type=Path,
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
    def run_from_argv(cls, argv: list[str]) -> None:
        self = cls()
        parser = self.create_parser(argv[0], argv[1])

        options = parser.parse_args(argv[2:])
        cmd_options = vars(options)
        # Move positional args out of options to mimic legacy optparse
        args = cmd_options.pop('args', ())

        self.execute(*args, **cmd_options)

    @classmethod
    def print_help(cls, prog_name: str, subcommand: str) -> None:
        """
        Print the help message for this command, derived from
        ``self.usage()``.
        """
        install = cls()
        parser = install.create_parser(prog_name, subcommand)
        parser.print_help()

    def write_conf_file(self):
        import yaml

        with self.output_file.open('w') as f:
            f.write('# This file contains SECRET information!\n')
            f.write('# Keep the contents of the file private,\n')
            f.write('# especially for production instances.\n')
            f.write('# DO NOT commit this file.\n\n')
            yaml.dump(vars(self.settings), f, default_flow_style=False)

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

    def create_conda_env(self, options) -> None:
        import json

        python_requirements = self.get_python_version()

        conda: str = options['conda']

        conda_info = json.loads(
            subprocess.run(
                [conda, 'info', '--json'],  # noqa: S603
                check=True,
                capture_output=True,
            ).stdout,
        )

        # build the env create command
        install_cmd: list[str] = [
            conda,
            'create',
            '-y',
            '-n',
            self.settings.CONDA_ENV_NAME,
            f'python{python_requirements}',
        ]

        if options.get('overwrite_env'):
            install_cmd.append('--force')

        if options.get('install_conda_req'):
            install_cmd.extend(['--file', options.get('conda_requirements')])

        # if overwrite_env isn't set to replace an existing env,
        # then we want to check for the env and fail if exists
        if not options.get('overwrite_env') and self.settings.CONDA_ENV_NAME in [
            Path(env).name for env in conda_info['envs']
        ]:
            raise InstallError(
                'A conda env of name '
                f'{self.settings.CONDA_ENV_NAME} already exists.',
            )

        self.vprint(
            2,
            'creating conda env with the following command:' f'{install_cmd}',
        )

        # now we create the env
        subprocess.run(install_cmd, check=True)  # noqa: S603
        self.env_root: Path = (
            Path(conda_info['sys.prefix']) / 'envs' / self.settings.CONDA_ENV_NAME
        )

        self.vprint(1, f'conda env created at {self.env_root}')

    def install(self) -> None:
        pip = self.get_pip()

        # install deps
        cmd: list[str] = [
            pip,
            'install',
            '-r',
            str(utils.PROJECT_ROOT / 'requirements.txt'),
        ]
        self.vprint(
            2,
            'Processing the following command for install:\n' f'{cmd}',
        )
        subprocess.run(cmd, check=True)  # noqa: S603

        # install app
        cmd = [
            pip,
            'install',
            '-e',
            str(utils.PROJECT_ROOT),
        ]
        self.vprint(
            2,
            'Processing the following command for install:\n' f'{cmd}',
        )
        subprocess.run(cmd, check=True)  # noqa: S603

    def get_pip(self) -> str:
        if hasattr(self, 'env_root'):
            return str(self.env_root / 'Scripts' / 'pip.exe')
        return 'pip'

    def print_conf(self) -> None:
        if self.verbosity and self.verbosity < 2:
            return
        print('Using the following configuration settings:', flush=True)  # noqa: T201
        for key, val in sorted(self.settings.__dict__.items()):
            if 'secret' in key.lower() or 'password' in key.lower():
                val = '************'
            print(f'    {key} = {val}', flush=True)  # noqa: T201

    def vprint(self, level, *args, **kwargs) -> None:
        kwargs['flush'] = True
        if self.verbosity >= level:
            print(*args, **kwargs)  # noqa: T201

    def snodas_command_error(self) -> None:
        project_root = utils.PROJECT_ROOT
        project_root_message = (
            ''
            if project_root == Path.cwd()
            else f" from the project's root directory {project_root}"
        )

        print(  # noqa: T201
            'Unfortunately, the install command must be run '
            "using the project's manage.py script instead of "
            'the snodas command. Try running '
            f'`python manage.py install`{project_root_message}.',
            flush=True,
        )

    def execute(self, *_, **options) -> int:
        if Path(sys.argv[0]).name == 'snodas':
            self.snodas_command_error()
            return 1

        self.verbosity: int = options['verbosity']

        self.output_file: Path = utils.get_default(
            options,
            'output_file',
            self.default_conf_file(),
        )

        self.vprint(2, f'Config file path will be {self.output_file}')

        conf_exists: bool = self.output_file.exists()

        if options['no_configure'] and conf_exists:
            self.vprint(1, f'Reusing existing configuration from {self.output_file}')
            self.settings = Settings(**utils.load_conf_file(self.output_file))
        elif options['no_configure'] and not conf_exists:
            print(  # noqa: T201
                'ERROR: no-configure option specified '
                'but configuration file does not exist.',
            )
            return 3
        elif conf_exists and not options['overwrite_conf']:
            print(  # noqa: T201
                'ERROR: configuration file already exists '
                'and overwrite-conf option not specified.',
            )
            return 4
        else:
            self.vprint(1, 'Generating configuration from install options')
            self.settings = Settings.from_options(**options)

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
            '\nNext, activate the new conda env for the project:\n\n'
            f'`conda activate {self.settings.PROJECT_NAME}`\n\n'
            'Then, setup any required services for this instance:\n\n'
            '`snodas createrasterdb INPUT_DEM  # creates raster db`\n'
            '`snodas createdb [options]  # creates a postgres DB`\n'
            '`snodas setupiis [options]  # creates a site in IIS`\n\n'
            'Once the services are configured, '
            'you can run a webserver:\n\n'
            '`snodas runserver [options]'
            'To learn what options apply to each command, try:\n\n'
            '`snodas help <command>`',
        )

        return 0


# Unlike the Install class above, this is actually a django command.
# It uses parts of the Install class to provide a way to integrate
# the install command into the manage.py command display, for the
# sake of a consistent user experience/documentation. It is never
# intended to be executed, and it will raise an error if attempted.
if BaseCommand:

    class Command(BaseCommand):
        help = Install.help

        requires_system_checks = []  # type: ignore  # noqa: RUF012

        def create_parser(self, prog_name, subcommand):
            """
            Create and return the ``ArgumentParser`` which will be used to
            parse the arguments to this command. We use the default definition
            from the django source, but we drop all the options because we
            don't want to display options that are not supported.
            """
            parser = CommandParser(
                prog=f'{Path(prog_name).name} {subcommand}',
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
                print(  # noqa: T201
                    '\n**PLEASE NOTE: the install command must be run '
                    "using the project's manage.py script instead of "
                    'the snodas command.**\n',
                )
            super().print_help(prog_name, subcommand)

        def handle(self, *_, **__):
            raise CommandError(
                'If you got here then you are not running the snodas '
                'manage.py script for your commands. Do not call '
                'install from django-admin.',
            )
