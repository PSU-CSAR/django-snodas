# Script originally from the "FastCGI Windows Server Django installation command"
# https://github.com/antoinemartin/django-windows-tools/blob/master/django_windows_tools/management/commands/winfcgi_install.py
#
# Copyright (c) 2017 - 2023 Jarrett Keifer
# Copyright (c) 2012 Openance SARL
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
import os
import subprocess
import sys

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template import Context, Template

from snodas.management.utils import PROJECT_ROOT

CONFIG_FILE_NAME = 'generated.web.config'
WAITRESS_SERVER = 'run_waitress_server.py'

WEB_CONFIG_STRING = r"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="HTTP to HTTPS Redirect" enabled="true" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions logicalGrouping="MatchAny">
                        <add input="{SERVER_PORT_SECURE}" pattern="^0$" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" redirectType="Permanent" />
                </rule>
            </rules>
        </rewrite>
        <handlers>
            <add name="httpPlatformHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified" requireAccess="Script" />
        </handlers>

        <httpPlatform processPath="{{ conda_exe }}" arguments="run --prefix {{ conda_env_path }} python .\{{ waitress_server }}" startupTimeLimit="120" startupRetryCount="3" requestTimeout="00:04:00" stdoutLogEnabled="true" stdoutLogFile=".\log\httpplatform-stdout">
            <environmentVariables>
                <environmentVariable name="PORT" value="%HTTP_PLATFORM_PORT%" />
            </environmentVariables>
        </httpPlatform>
    </system.webServer>
</configuration>
"""  # noqa: E501


class Command(BaseCommand):
    help = """Installs the current project as an IIS site.

    If the root path is not specified, the command will take the
    root directory of the project.

    Don't forget to run this command as Administrator
    """

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Deletes the configuration instead of creating it',
        )
        parser.add_argument(
            '--site-name',
            dest='site_name',
            default='',
            help='IIS site name (defaults to name of installation directory)',
        )
        parser.add_argument(
            '--binding',
            dest='binding',
            help='IIS site binding. ' 'Defaults to https://<project_domain_name>:443',
        )
        parser.add_argument(
            '--skip-site',
            action='store_true',
            dest='skip_site',
            default=False,
            help='Skips the site creation',
        )
        parser.add_argument(
            '--skip-config',
            action='store_true',
            dest='skip_config',
            default=False,
            help='Skips the configuration creation',
        )
        parser.add_argument(
            '--log-dir',
            dest='log_dir',
            default='',
            help=r'Directory for IIS logfiles '
            r'(defaults to %SystemDrive%\inetpub\logs\LogFiles)',
        )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.appcmd = (
            Path(os.environ['WINDIR'])
            / 'system32'
            / 'inetsrv'
            / 'appcmd.exe'
        )
        self.project_dir = PROJECT_ROOT
        self.web_config = self.project_dir / CONFIG_FILE_NAME

        python_interpreter = Path(sys.executable)
        self.conda_env_path = python_interpreter.parent
        self.conda_exe = self.conda_env_path.parent.parent / 'Scripts' / 'conda.exe'

        self.waitress_server = WAITRESS_SERVER
        self.last_command_error: str | None = None

        if not (self.conda_exe.is_file() and os.access(self.conda_exe, os.X_OK)):
            raise Exception(
                'IIS is currently only supported if running project from conda env',
            )

    def config_command(self, command, section, *args) -> subprocess.Popen[bytes]:
        arguments: list[str] = [str(self.appcmd), command, section]
        arguments.extend(args)
        return subprocess.Popen(
            arguments,  # noqa: S603
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_config_command(self, command, section, *args) -> bool:
        command_process = self.config_command(command, section, *args)
        out, _ = command_process.communicate()
        result: bool = command_process.returncode == 0
        self.last_command_error = out.decode() if not result else None
        return result

    def set_project_permissions(self) -> None:
        # set permissions on the root project directory for the IIS site user
        cmd: list[str] = [
            'ICACLS',
            str(self.project_dir),
            '/t',
            '/grant',
            rf'IIS AppPool\{settings.PROJECT_NAME}:F',
        ]
        subprocess.check_call(cmd)  # noqa: S603
        cmd = [
            'ICACLS',
            str(Path(sys.executable) / 'Library' / 'bin'),
            '/t',
            '/grant',
            rf'IIS AppPool\{settings.PROJECT_NAME}:F',
        ]
        subprocess.check_call(cmd)  # noqa: S603

    def install(self, **options) -> None:
        if self.web_config.exists() and not options['skip_config']:
            raise CommandError(
                f'A web site configuration already exists in {self.project_dir} !',
            )

        # create web.config
        if not options['skip_config']:
            print('Creating web.config')  # noqa: T201
            template = Template(WEB_CONFIG_STRING)
            self.web_config.write_text(template.render(Context(self.__dict__)))

        # Create sites
        if options['skip_site']:
            return

        site_name = options['site_name']
        print(f'Creating application pool with name {site_name}')  # noqa: T201
        if not self.run_config_command(
            'add',
            'apppool',
            f'/name:{site_name}',
        ):
            raise CommandError(
                'The Application Pool creation has failed with '
                'the following message :\n'
                f'{self.last_command_error}',
            )

        binding: str = options.get('binding', f'https://{settings.SITE_DOMAIN_NAME}:443')

        print('Creating the site')  # noqa: T201
        if not self.run_config_command(
            'add',
            'site',
            f'/name:{site_name}',
            f'/bindings:{binding}',
            f'/physicalPath:{self.project_dir}',
        ):
            raise CommandError(
                'The site creation has failed with the following message :\n'
                f'{self.last_command_error}',
            )

        print('Adding the site to the application pool')  # noqa: T201
        if not self.run_config_command(
            'set',
            'app',
            f'{site_name}/',
            f'/applicationPool:{site_name}',
        ):
            raise CommandError(
                'Adding the site to the application pool has failed '
                'with the following message :\n'
                f'{self.last_command_error}',
            )

        log_dir = options['log_dir']
        if log_dir and not self.run_config_command(
            'set',
            'site',
            f'{site_name}/',
            f'/logFile.directory:{log_dir}',
        ):
            raise CommandError(
                'Setting the logging directory has failed with '
                'the following message :\n'
                f'{self.last_command_error}',
            )

    def delete(self, **options) -> None:
        if not options['skip_config']:
            print('Removing site configuration')  # noqa: T201
            self.web_config.unlink(missing_ok=True)

        if not options['skip_site']:
            site_name = options['site_name']
            print('Removing The site')  # noqa: T201
            if not self.run_config_command('delete', 'site', site_name):
                raise CommandError(
                    'Removing the site has failed with the following message :\n'
                    f'{self.last_command_error}',
                )

            print('Removing The application pool')  # noqa: T201
            if not self.run_config_command('delete', 'apppool', site_name):
                raise CommandError(
                    'Removing the site has failed with the following message :\n'
                    f'{self.last_command_error}',
                )

    def handle(self, *_, **options) -> None:
        if options['site_name'] == '':
            options['site_name'] = settings.PROJECT_NAME

        if not self.appcmd.exists():
            raise CommandError(
                'It seems that IIS is not installed on your machine',
            )

        if options['delete']:
            self.delete(**options)
        else:
            self.install(**options)
            self.set_project_permissions()
            print(  # noqa: T201
                f"""
PLEASE NOTE: This command is unable to set
the certificate to use for the specified binding.
Please use the IIS tool to edit the binding and
set the correct certificate:

1) Open IIS
2) Expand the "Sites" in the left navigation panel
3) Right-click "{settings.PROJECT_NAME}" and choose "Edit Bindings"
4) Edit the binding and choose the correct SSL Certificate""",
            )


if __name__ == '__main__':
    print('This is supposed to be run as a django management command')  # noqa: T201
