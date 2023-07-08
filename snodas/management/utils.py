import argparse
import os
import random
import string
import yaml
import io


CONF_FILE_NAME = 'project.conf'
SETTINGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'settings',
)


def to_namedtuple(dictionary):
    from collections import namedtuple
    return namedtuple('GenericDict', list(dictionary.keys()))(**dictionary)


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


def chain_streams(streams, buffer_size=io.DEFAULT_BUFFER_SIZE, sep=b''):
    """
    Chain an iterable of streams together into a single buffered stream.
    Usage:
        def generate_open_file_streams():
            for file in filenames:
                yield open(file, 'rb')
        f = chain_streams(generate_open_file_streams())
        f.read()
    """
    _streams = []
    if sep:
        last = len(streams) - 1
        for idx, stream in enumerate(streams):
            _streams.append(stream)
            if idx != last:
                _streams.append(io.BytesIO(sep))
    else:
        _streams = streams

    class ChainStream(io.RawIOBase):
        def __init__(self):
            self.leftover = b''
            self.stream_iter = iter(_streams)
            try:
                self.stream = next(self.stream_iter)
            except StopIteration:
                self.stream = None

        def readable(self):
            return True

        def _read_next_chunk(self, max_length):
            # Return 0 or more bytes from the current stream, first returning all
            # leftover bytes. If the stream is closed returns b''
            if self.leftover:
                return self.leftover
            elif self.stream is not None:
                return self.stream.read(max_length)
            else:
                return b''

        def readinto(self, b):
            buffer_length = len(b)
            chunk = self._read_next_chunk(buffer_length)
            while len(chunk) == 0:
                # move to next stream
                if self.stream is not None:
                    self.stream.close()
                try:
                    self.stream = next(self.stream_iter)
                    chunk = self._read_next_chunk(buffer_length)
                except StopIteration:
                    # No more streams to chain together
                    self.stream = None
                    return 0  # indicate EOF
            output, self.leftover = chunk[:buffer_length], chunk[buffer_length:]
            b[:len(output)] = output
            return len(output)

    return io.BufferedReader(ChainStream(), buffer_size=buffer_size)
