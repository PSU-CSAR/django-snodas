import logging
import re

from django.http import HttpResponse, StreamingHttpResponse

from .filesystem import FileWrapper

CHUNK_SIZE = 2**15

logger = logging.getLogger(__name__)


def stream_file(filelike, filename, request, content_type):
    start, end = 0, None
    file_size = filelike.seek(0, 2)

    if 'HTTP_RANGE' in request.META:
        try:
            start, end = re.findall(r'/d+', request.META['HTTP_RANGE'])
        except TypeError:
            logger.exception(
                'Malformed HTTP_RANGE in download request: %s',
                request.META['HTTP_RANGE'],
            )
            return HttpResponse(
                status=416,
            )

        if start > end or end > file_size:
            return HttpResponse(
                status=416,
            )

    fwrapper = FileWrapper(
        filelike,
        blksize=CHUNK_SIZE,
        start=start,
        end=end,
    )
    response = StreamingHttpResponse(
        fwrapper,
        content_type=content_type,
    )
    response['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    response['Content-Length'] = file_size
    response['Accept-Ranges'] = 'bytes'

    if 'HTTP_RANGE' in request.META:
        response['status'] = 206
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'

    return response
