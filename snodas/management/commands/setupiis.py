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

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template import Context, Template

from ..utils import get_project_root

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
"""


def library_bin_dir(python_exe):
    return os.path.join(
        os.path.dirname(python_exe),
        'Library',
        'bin',
    )


class Command(BaseCommand):
    help = """Installs the current project as an IIS site.

    If the root path is not specified, the command will take the
    root directory of the project.

    Don't forget to run this command as Administrator
    """

    def add_arguments(self, parser):
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

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.appcmd = os.path.join(
            os.environ['windir'],
            'system32',
            'inetsrv',
            'appcmd.exe',
        )
        self.project_dir = os.path.abspath(get_project_root())
        self.web_config = os.path.join(self.project_dir, CONFIG_FILE_NAME)

        python_interpreter = sys.executable
        self.conda_env_path = os.path.dirname(python_interpreter)
        self.conda_exe = os.path.join(
            os.path.dirname(os.path.dirname(self.conda_env_path)),
            'Scripts',
            'conda.exe',
        )

        self.waitress_server = WAITRESS_SERVER
        self.last_command_error = None

        if not (os.path.isfile(self.conda_exe) and os.access(self.conda_exe, os.X_OK)):
            raise Exception(
                'IIS is currently only supported if running project from conda env'
            )

    def config_command(self, command, section, *args):
        arguments = [self.appcmd, command, section]
        arguments.extend(args)
        return subprocess.Popen(
            arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_config_command(self, command, section, *args):
        command_process = self.config_command(command, section, *args)
        (out, err) = command_process.communicate()
        result = command_process.returncode == 0
        self.last_command_error = out if not result else None
        return result

    def set_project_permissions(self):
        # set permissions on the root project directory for the IIS site user
        cmd = [
            'ICACLS',
            get_project_root(),
            '/t',
            '/grant',
            rf'IIS AppPool\{settings.PROJECT_NAME}:F',
        ]
        subprocess.check_call(cmd)
        cmd = [
            'ICACLS',
            library_bin_dir(sys.executable),
            '/t',
            '/grant',
            rf'IIS AppPool\{settings.PROJECT_NAME}:F',
        ]
        subprocess.check_call(cmd)

    def install(self, args, options):
        if os.path.exists(self.web_config) and not options['skip_config']:
            raise CommandError(
                'A web site configuration already exists in [%s] !' % self.project_dir,
            )

        # create web.config
        if not options['skip_config']:
            print('Creating web.config')
            template = Template(WEB_CONFIG_STRING)
            with open(self.web_config, 'w') as f:
                f.write(template.render(Context(self.__dict__)))

        # Create sites
        if not options['skip_site']:
            site_name = options['site_name']
            print('Creating application pool with name %s' % site_name)
            if not self.run_config_command('add', 'apppool', '/name:%s' % site_name):
                raise CommandError(
                    'The Application Pool creation has failed with the following message :\n%s'
                    % self.last_command_error,
                )

            binding = (
                options.get('binding')
                or '{}://{}:{}'.format(
                    'https',
                    settings.SITE_DOMAIN_NAME,
                    443,
                ),
            )

            print('Creating the site')
            if not self.run_config_command(
                'add',
                'site',
                '/name:%s' % site_name,
                '/bindings:%s' % binding,
                '/physicalPath:%s' % self.project_dir,
            ):
                raise CommandError(
                    'The site creation has failed with the following message :\n%s'
                    % self.last_command_error,
                )

            print('Adding the site to the application pool')
            if not self.run_config_command(
                'set', 'app', '%s/' % site_name, '/applicationPool:%s' % site_name
            ):
                raise CommandError(
                    'Adding the site to the application pool has failed with the following message :\n%s'
                    % self.last_command_error,
                )

            if static_is_local and static_needs_virtual_dir:
                print(
                    'Creating virtual directory for [%s] in [%s]'
                    % (static_dir, static_url)
                )
                if not self.run_config_command(
                    'add',
                    'vdir',
                    '/app.name:%s/' % site_name,
                    '/path:/%s' % static_name,
                    '/physicalPath:%s' % static_dir,
                ):
                    raise CommandError(
                        'Adding the static virtual directory has failed with the following message :\n%s'
                        % self.last_command_error,
                    )

            log_dir = options['log_dir']
            if log_dir:
                if not self.run_config_command(
                    'set', 'site', '%s/' % site_name, '/logFile.directory:%s' % log_dir
                ):
                    raise CommandError(
                        'Setting the logging directory has failed with the following message :\n%s'
                        % self.last_command_error,
                    )

    def delete(self, args, options):
        if not os.path.exists(self.web_config) and not options['skip_config']:
            raise CommandError(
                'A web site configuration does not exists in [%s] !' % self.project_dir
            )

        if not options['skip_config']:
            print('Removing site configuration')
            os.remove(self.web_config)

        if not options['skip_site']:
            site_name = options['site_name']
            print('Removing The site')
            if not self.run_config_command('delete', 'site', site_name):
                raise CommandError(
                    'Removing the site has failed with the following message :\n%s'
                    % self.last_command_error,
                )

            print('Removing The application pool')
            if not self.run_config_command('delete', 'apppool', site_name):
                raise CommandError(
                    'Removing the site has failed with the following message :\n%s'
                    % self.last_command_error,
                )

    def handle(self, *args, **options):
        if options['site_name'] == '':
            options['site_name'] = settings.PROJECT_NAME

        if not os.path.exists(self.appcmd):
            raise CommandError(
                'It seems that IIS is not installed on your machine',
            )

        if options['delete']:
            self.delete(args, options)
        else:
            self.install(args, options)
            self.set_project_permissions()
            print(
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
    print('This is supposed to be run as a django management command')
