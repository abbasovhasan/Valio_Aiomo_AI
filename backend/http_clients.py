"""Bounded reusable connections; credentials and facts remain request-scoped.

Only transport connections are reused. Every caller supplies its current auth,
payload and timeout, and every commercial lookup still reaches the provider.
"""
import atexit
import threading
from contextlib import contextmanager

import httpx

_clients = {}
_lock = threading.Lock()


def _client(service):
    if service not in {"nvidia", "valio"}:
        raise ValueError("Unknown external transport")
    with _lock:
        client = _clients.get(service)
        if client is None or client.is_closed:
            def drop_cookie_header(request):
                # Provider sessions must never migrate between customer requests.
                request.headers.pop("cookie", None)

            def discard_response_cookies(response):
                client.cookies.clear()

            client = httpx.Client(
                follow_redirects=False,
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2, keepalive_expiry=30),
                event_hooks={"request": [drop_cookie_header], "response": [discard_response_cookies]},
            )
            _clients[service] = client
        return client


@contextmanager
def provider_client(service):
    # A request borrows the process client; leaving its scope must not close the
    # pool. httpx clients support concurrent use; application write policy is
    # unchanged and does not gain parallel Modal inputs from this helper.
    yield _client(service)


def close_clients():
    with _lock:
        for client in _clients.values():
            client.close()
        _clients.clear()


atexit.register(close_clients)
