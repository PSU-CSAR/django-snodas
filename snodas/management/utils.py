from __future__ import absolute_import

import argparse
import os
import random
import string
import yaml


CONF_FILE_NAME = 'project.conf'
SETTINGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'settings',
)


def to_namedtuple(dictionary):
    from collections import namedtuple
    return namedtuple('GenericDict', dictionary.keys())(**dictionary)


def get_default(dictionary, key, default=None):
    val = dictionary.get(key, None)
    return val if val is not None else default


def generate_secret_key(length=50):
    choices = '{}{}{}'.format(
        string.ascii_letters,
        string.digits,
        string.punctuation.replace('\'', '').replace('\\', ''),
    )
    return ''.join(
        [random.SystemRandom().choice(choices) for i in range(length)]
    )


def destruct_path(path):
    '''take a path and break it's pieces into a list:
    d:\projects\snodas\development becomes
    ['d:', 'projects', 'snodas', 'development']'''

    folders = []
    while True:
        path, folder = os.path.split(path)

        if folder != "":
            folders.append(folder)
        else:
            if path != "":
                folders.append(path)

            break

    return folders[::-1]


def get_project_root():
    # path should look something like
    # d:\development\snodas_dev\django-snodas\snodas\settings
    # which should be split into separate elements in a list
    # the project root is 4th from the end, which we use to slice and
    # reconstruct into d:\development\snodas_dev\django-snodas
    return os.path.join(*destruct_path(SETTINGS_DIR)[:-2])


def get_instance_name():
    try:
        # path should look something like
        # d:\development\snodas_dev\django-snodas\snodas\settings
        # which should be split into separate elements in a list
        # the instance name is 5th from the end (snodas_dev)
        return destruct_path(SETTINGS_DIR)[-4]
    except IndexError:
        # path was too short and we couldn't get anything from it
        return None


def get_env_name():
    try:
        # path should look something like
        # d:\development\snodas_dev\django-snodas\snodas\settings
        # which should be split into separate elements in a list
        # the instance name is 6th from the end (development)
        return destruct_path(SETTINGS_DIR)[-5]
    except IndexError:
        # path was too short and we couldn't get anything from it
        return None


def get_settings_file(file_name=None):
    if file_name:
        return os.path.join(
            SETTINGS_DIR,
            file_name,
        )
    return SETTINGS_DIR


def load_conf_file(config=os.path.join(get_project_root(), CONF_FILE_NAME)):
    try:
        with open(config, 'r') as f:
            return yaml.safe_load(f)
    except (IOError, OSError):
        raise Exception((
            'Could not load project configuration file {}. '
            'Have you installed this snodas instance?'
        ).format(config))


class FullPaths(argparse.Action):
    """Expand user- and relative-paths"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def is_dir(dirname):
    """Checks if a path is an actual directory"""
    if not os.path.isdir(dirname):
        msg = "{0} is not a directory".format(dirname)
        raise argparse.ArgumentTypeError(msg)
    else:
        return dirname


def is_file(name):
    """Checks if a path is an actual file"""
    if not os.path.isfile(name):
        msg = "{0} is not a file".format(name)
        raise argparse.ArgumentTypeError(msg)
    else:
        return name
