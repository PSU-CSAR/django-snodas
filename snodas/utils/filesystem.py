from contextlib import contextmanager


@contextmanager
def tempdirectory(suffix='', prefix='', dir=None, do_not_remove=False):
    """A context manager for creating a temporary directory
    that will automatically be removed when it is no longer
    in context."""
    from shutil import rmtree
    from tempfile import mkdtemp

    tmpdir = mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
    was_exception = False
    try:
        yield tmpdir
    except Exception as e:
        was_exception = True
        raise e
    finally:
        if not do_not_remove or not was_exception:
            rmtree(tmpdir)


class FileWrapper:
    """Wrapper to convert file-like objects to iterables,
    based on the FileWrapper class from wsgiref, but modified to
    take a start and end point to allow serving byte ranges in
    addition to whole files. Also fixes __getitem__ method to
    actaully work as a getitem function should, so API is not
    exactly the same as the wsgiref implementation."""

    def __init__(self, filelike, blksize=8192, start=0, end=None):
        self.filelike = filelike
        self.blocksize = blksize
        self.start = start
        self.filelike.seek(start)
        self.end = end

        # get methods off filelike
        self.tell = filelike.tell
        self.read = filelike.read
        if hasattr(filelike, ' close'):
            self.close = filelike.close

    def __getitem__(self, key):
        return self._read(key=key)

    def __iter__(self):
        return self

    def _read(self, key=None):
        blocksize = self.blocksize
        current_position = self.tell()

        if key:
            self.seek(blocksize * key)

        if self.end and self.tell() + self.blocksize > self.end:
            blocksize = self.end - self.tell()

        data = self.read(blocksize)

        if key:
            self.seek(current_position)

        if data:
            return data

        raise IndexError

    def seek(self, position):
        position += self.start
        self.filelike.seek(position)

    def __next__(self):
        try:
            return self._read()
        except IndexError as e:
            raise StopIteration from e
