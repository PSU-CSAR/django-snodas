from __future__ import absolute_import

import os

from logging.handlers import RotatingFileHandler as lgRotatingFileHandler

from .filesystem import makedirs


class RotatingFileHandler(lgRotatingFileHandler):
    def __init__(self, filename, *args, **kwargs):
        if kwargs.pop('makedirs', False):
            makedirs(os.path.dirname(filename), exist_ok=True)
        super(RotatingFileHandler, self).__init__(
            filename, *args, **kwargs
        )
