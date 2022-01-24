import contextlib
import multiprocessing
import socket

from werkzeug import Request, Response, run_simple


def get_token(q: multiprocessing.Queue, port: int) -> None:
    @Request.application
    def app(request: Request) -> Response:
        q.put(request.args)
        return Response('You may close this tab and return to your application.', status=200)

    run_simple("127.0.0.1", port, app)


def _find_free_port():
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('', 0))
        return sock.getsockname()[1]
