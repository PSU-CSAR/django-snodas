import argparse
import random
import string

from pathlib import Path

import yaml

CONF_FILE_NAME = 'project.conf'
THIS = Path(__file__).resolve()
SETTINGS_DIR = THIS.parent.parent / 'settings'
PROJECT_ROOT = SETTINGS_DIR.parent.parent
CONF_FILE = PROJECT_ROOT / CONF_FILE_NAME


def get_default(dictionary, key, default=None):
    val = dictionary.get(key, None)
    return val if val is not None else default


def generate_secret_key(length=50):
    choices = '{}{}{}'.format(
        string.ascii_letters,
        string.digits,
        string.punctuation.replace("'", '').replace('\\', ''),
    )
    return ''.join(
        [random.SystemRandom().choice(choices) for _ in range(length)],
    )


def get_project_root():
    return PROJECT_ROOT


def get_settings_file(file_name=None):
    return SETTINGS_DIR / file_name if file_name else SETTINGS_DIR


def load_conf_file(config=CONF_FILE):
    try:
        with config.open() as f:
            return yaml.safe_load(f)
    except OSError as e:
        raise Exception(
            f'Could not load project configuration file {config}. '
            'Have you installed this snodas instance?',
        ) from e


def directory(dirname: str) -> Path:
    """Checks if a path is an actual directory"""
    d = Path(dirname).expanduser().resolve()

    if not d.is_dir():
        msg = f'{dirname} is not a directory'
        raise argparse.ArgumentTypeError(msg)

    return d


def file(name: str) -> Path:
    """Checks if a path is an actual file"""
    f = Path(name).expanduser().resolve()

    if not f.is_file():
        msg = f'{name} is not a file'
        raise argparse.ArgumentTypeError(msg)

    return f


def path_exists(name: str) -> Path:
    """Checks if a path exists, irrespective of type"""
    f = Path(name).expanduser().resolve()

    if not f.exists():
        msg = f'{name} does not exist'
        raise argparse.ArgumentTypeError(msg)

    return f
