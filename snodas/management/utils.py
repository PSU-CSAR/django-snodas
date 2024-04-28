import argparse
import io
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


class ChainStream(io.RawIOBase):
    def __init__(self, streams):
        self.leftover = b''
        self.stream_iter = iter(streams)
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

        if self.stream is not None:
            return self.stream.read(max_length)

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
        b[: len(output)] = output
        return len(output)


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

    return io.BufferedReader(ChainStream(_streams), buffer_size=buffer_size)
