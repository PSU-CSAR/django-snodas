from logging.handlers import RotatingFileHandler as lgRotatingFileHandler
from pathlib import Path


class RotatingFileHandler(lgRotatingFileHandler):
    def __init__(self, filename, *args, **kwargs):
        if kwargs.pop('makedirs', False):
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(
            filename,
            *args,
            **kwargs,
        )
