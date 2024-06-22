import io


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
