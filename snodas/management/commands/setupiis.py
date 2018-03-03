# encoding: utf-8

# FastCGI Windows Server Django installation command
#
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
from __future__ import print_function, absolute_import

import os
import sys
import re
import subprocess

from django.template import Template, Context
from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.contrib.staticfiles.management.commands import collectstatic

from ..utils import get_project_root


MAX_CONTENT_LENGTH = 2**30

TOUCH_FILE = os.path.join(get_project_root(),
                          'touch_this_file_to_update_cgi.txt')

CONFIG_FILE_NAME = 'web.config'

STATIC_CONFIG = os.path.join(settings.STATIC_ROOT, CONFIG_FILE_NAME)
STATIC_CONFIG_STRING = \
'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <!-- this configuration overrides the FastCGI handler to let IIS serve the static files -->
    <handlers>
    <clear/>
      <add name="StaticFile" path="*" verb="*" modules="StaticFileModule" resourceType="File" requireAccess="Read" />
    </handlers>
  </system.webServer>
</configuration>
'''

#     <security>
#      <requestFiltering>
#        <requestLimits maxAllowedContentLength="{{  }}"/>
#      </requestFiltering>
#    </security>

WEB_CONFIG_STRING = \
'''<?xml version="1.0" encoding="UTF-8"?>
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
           <clear/>
           <add name="FastCGI" path="*" verb="*" modules="FastCgiModule" scriptProcessor="{{ python_interpreter }}|{{ current_script }} winfcgi --pythonpath={{ project_dir }}" resourceType="Unspecified" requireAccess="Script" />
       </handlers>
    </system.webServer>
</configuration>'''


def library_bin_dir(python_exe):
    return os.path.join(
        os.path.dirname(python_exe),
        "Library",
        "bin",
    )


class Command(BaseCommand):
    help = '''Installs the current application as a fastcgi application under windows.

    If the root path is not specified, the command will take the
    root directory of the project.

    Don't forget to run this command as Administrator
    '''

    CONFIGURATION_TEMPLATE = '''/+[fullPath='{python_interpreter}',arguments='{script} winfcgi --pythonpath={project_dir}',maxInstances='{maxInstances}',idleTimeout='{idleTimeout}',activityTimeout='{activityTimeout}',requestTimeout='{requestTimeout}',instanceMaxRequests='{instanceMaxRequests}',protocol='NamedPipe',flushNamedPipe='False',monitorChangesTo='{monitorChangesTo}']'''

    DELETE_TEMPLATE = '''/[arguments='{script} winfcgi --pythonpath={project_dir}']'''

    FASTCGI_SECTION = 'system.webServer/fastCgi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Deletes the configuration instead of creating it',
        )
        parser.add_argument(
            '--max-instances',
            dest='maxInstances',
            default=4,
            help='Maximum number of pyhton processes',
        )
        parser.add_argument(
            '--idle-timeout',
            dest='idleTimeout',
            default=1800,
            help='Idle time in seconds after which a python '
                 'process is recycled',
        )
        parser.add_argument(
            '--max-content-length',
            dest='maxContentLength',
            default=MAX_CONTENT_LENGTH,
            help='Maximum allowed request content length size',
        )
        parser.add_argument(
            '--activity-timeout',
            dest='activityTimeout',
            default=30,
            help='Number of seconds without data transfer after '
                 'which a process is stopped',
        )
        parser.add_argument(
            '--request-timeout',
            dest='requestTimeout',
            default=90,
            help='Total time in seconds for a request',
        )
        parser.add_argument(
            '--instance-max-requests',
            dest='instanceMaxRequests',
            default=10000,
            help='Number of requests after which a python '
                 'process is recycled',
        )
        parser.add_argument(
            '--monitor-changes-to',
            dest='monitorChangesTo',
            default='',
            help='Application is restarted when this file changes. '
                 'Default is to watch the web.config file '
                 '(touch it to restart the cgi process for updates).',
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
            help='IIS site binding. '
                 'Defaults to https://<project_domain_name>:443',
        )
        parser.add_argument(
            '--skip-fastcgi',
            action='store_true',
            dest='skip_fastcgi',
            default=False,
            help='Skips the FastCGI application installation',
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
            os.environ['windir'], 'system32', 'inetsrv', 'appcmd.exe',
        )
        self.current_script = os.path.abspath(sys.argv[0])
        self.project_dir, self.script_name = os.path.split(self.current_script)
        self.python_interpreter = sys.executable
        self.last_command_error = None

    def config_command(self, command, section, *args):
        arguments = [self.appcmd, command, section]
        arguments.extend(args)
        return subprocess.Popen(
            arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def run_config_command(self, command, section, *args):
        command_process = self.config_command(command, section, *args)
        (out, err) = command_process.communicate()
        result = command_process.returncode == 0
        self.last_command_error = out if not result else None
        return result

    def check_config_section_exists(self, section_name):
        return self.run_config_command(
            'list', 'config', '-section:%s' % section_name,
        )

    def create_fastcgi_section(self, options):
        template_options = options.copy()
        template_options['script'] = self.current_script
        template_options['project_dir'] = self.project_dir
        template_options['python_interpreter'] = self.python_interpreter
        param = self.CONFIGURATION_TEMPLATE.format(**template_options)
        return self.run_config_command(
            'set',
            'config',
            '-section:%s' % self.FASTCGI_SECTION,
            param,
            '/commit:apphost',
        )

    def delete_fastcgi_section(self):
        template_options = dict(
            script=self.current_script,
            project_dir=self.project_dir,
        )
        param = self.DELETE_TEMPLATE.format(**template_options)
        return self.run_config_command(
            'clear',
            'config',
            '-section:%s' % self.FASTCGI_SECTION,
            param,
            '/commit:apphost',
        )

    def create_touch_file(self, delete=False):
        if delete:
            os.remove(TOUCH_FILE)
            return

        with open(TOUCH_FILE, 'w') as f:
            f.write('')

    def setup_static_assets(self, delete=False):
        if delete:
            os.remove(STATIC_CONFIG)
            return

        # get the static assets to setup proj and create static dir
        management.call_command(collectstatic.Command(), verbosity=0)
        # place the IIS conf file in the static dir
        with open(STATIC_CONFIG, 'w') as f:
            f.write(STATIC_CONFIG_STRING)

    def set_project_permissions(self):
        # set permissions on the root project directory for the IIS site user
        cmd = ['ICACLS', get_project_root(), '/t', '/grant',
               'IIS AppPool\{}:F'.format(settings.INSTANCE_NAME)]
        subprocess.check_call(cmd)
        cmd = ['ICACLS', library_bin_dir(sys.executable), '/t', '/grant',
               'IIS AppPool\{}:F'.format(settings.INSTANCE_NAME)]
        subprocess.check_call(cmd)

    def install(self, args, options):
        if os.path.exists(self.web_config) and not options['skip_config']:
            raise CommandError(
                'A web site configuration already exists in [%s] !' % self.install_dir,
            )

        # now getting static files directory and URL
        static_dir = os.path.normcase(
            os.path.abspath(getattr(settings, 'STATIC_ROOT', ''))
        )
        static_url = getattr(settings, 'STATIC_URL', '/static/')

        static_match = re.match('^/([^/]+)/$', static_url)
        if static_match:
            static_is_local = True
            static_name = static_match.group(1)
            static_needs_virtual_dir = static_dir != \
                os.path.join(self.install_dir, static_name)
        else:
            static_is_local = False

        if static_dir == self.install_dir and static_is_local:
            raise CommandError('''\
The web site directory cannot be the same as the static directory,
for we cannot have two different web.config files in the same
directory !''')

        # create web.config
        if not options['skip_config']:
            print("Creating web.config")
            template = Template(WEB_CONFIG_STRING)
            with open(self.web_config, 'w') as f:
                f.write(template.render(Context(self.__dict__)))

        if options['monitorChangesTo'] == '':
            options['monitorChangesTo'] = os.path.join(
                self.install_dir, 'web.config'
            )

        # create FastCGI application
        if not options['skip_fastcgi']:
            print("Creating FastCGI application")
            if not self.create_fastcgi_section(options):
                raise CommandError(
                    'The FastCGI application creation has failed with the following message :\n%s' % self.last_command_error
                )

        # Create sites
        if not options['skip_site']:
            site_name = options['site_name']
            print("Creating application pool with name %s" % site_name)
            if not self.run_config_command('add', 'apppool', '/name:%s' % site_name):
                raise CommandError(
                    'The Application Pool creation has failed with the following message :\n%s' % self.last_command_error
                )

            binding = options.get('binding') or '{}://{}:{}'.format(
                'https',
                settings.SITE_DOMAIN_NAME,
                443,
            ),

            print("Creating the site")
            if not self.run_config_command('add', 'site', '/name:%s' % site_name, '/bindings:%s' % binding,
                                           '/physicalPath:%s' % self.install_dir):
                raise CommandError(
                    'The site creation has failed with the following message :\n%s' % self.last_command_error
                )

            print("Adding the site to the application pool")
            if not self.run_config_command('set', 'app', '%s/' % site_name, '/applicationPool:%s' % site_name):
                raise CommandError(
                    'Adding the site to the application pool has failed with the following message :\n%s' % self.last_command_error
                )

            if static_is_local and static_needs_virtual_dir:
                print("Creating virtual directory for [%s] in [%s]" % (static_dir, static_url))
                if not self.run_config_command('add', 'vdir', '/app.name:%s/' % site_name, '/path:/%s' % static_name,
                                               '/physicalPath:%s' % static_dir):
                    raise CommandError(
                        'Adding the static virtual directory has failed with the following message :\n%s' % self.last_command_error
                    )

            log_dir = options['log_dir']
            if log_dir:
                if not self.run_config_command('set', 'site', '%s/' % site_name, '/logFile.directory:%s' % log_dir):
                    raise CommandError(
                        'Setting the logging directory has failed with the following message :\n%s' % self.last_command_error
                     )

            maxContentLength = options['maxContentLength']
            if not self.run_config_command('set', 'config', '%s' % site_name, '/section:requestfiltering',
                                           '/requestlimits.maxallowedcontentlength:' + str(maxContentLength)):
                raise CommandError(
                    'Setting the maximum content length has failed with the following message :\n%s' % self.last_command_error
                )

    def delete(self, args, options):
        if not os.path.exists(self.web_config) and not options['skip_config']:
            raise CommandError('A web site configuration does not exists in [%s] !' % self.install_dir)

        if not options['skip_config']:
            print("Removing site configuration")
            os.remove(self.web_config)

        if not options['skip_site']:
            site_name = options['site_name']
            print("Removing The site")
            if not self.run_config_command('delete', 'site', site_name):
                raise CommandError(
                    'Removing the site has failed with the following message :\n%s' % self.last_command_error
                )

            print("Removing The application pool")
            if not self.run_config_command('delete', 'apppool', site_name):
                raise CommandError(
                    'Removing the site has failed with the following message :\n%s' % self.last_command_error
                )

        if not options['skip_fastcgi']:
            print("Removing FastCGI application")
            if not self.delete_fastcgi_section():
                raise CommandError('The FastCGI application removal has failed'
            )

    def handle(self, *args, **options):
        # Getting installation directory and doing some little checks
        self.install_dir = get_project_root()
        if not os.path.exists(self.install_dir):
            raise CommandError(
                'The web site directory [%s] does not exist !' % self.install_dir
            )

        if not os.path.isdir(self.install_dir):
            raise CommandError(
                'The web site directory [%s] is not a directory !' % self.install_dir
            )

        self.install_dir = os.path.normcase(os.path.abspath(self.install_dir))

        print('Using installation directory %s' % self.install_dir)

        self.web_config = os.path.join(self.install_dir, 'web.config')

        if options['site_name'] == '':
            options['site_name'] = settings.INSTANCE_NAME

        if not os.path.exists(self.appcmd):
            raise CommandError(
                'It seems that IIS is not installed on your machine'
            )

        if not self.check_config_section_exists(self.FASTCGI_SECTION):
            raise CommandError(
                'Failed to detect the CGI module with the following message:\n%s' % self.last_command_error
            )

        self.setup_static_assets(delete=options.get('delete'))
        self.create_touch_file(delete=options.get('delete'))

        if options['delete']:
            self.delete(args, options)
        else:
            self.install(args, options)

        self.set_project_permissions()

        if not options['delete']:
            print('''
PLEASE NOTE: This command is unable to set
the certificate to use for the specified binding.
Please use the IIS tool to edit the binding and
set the correct certificate:

1) Open IIS
2) Expand the "Sites" in the left navigation panel
3) Right-click "{}" and choose "Edit Bindings"
4) Edit the binding and choose the correct SSL Certificate'''.format(
            settings.INSTANCE_NAME)
        )


if __name__ == '__main__':
    print('This is supposed to be run as a django management command')
