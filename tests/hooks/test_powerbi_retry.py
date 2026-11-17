import socket
import threading
import unittest

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import ReadTimeoutError

from PowerBI_Operator.hooks.powerbi_retry import PowerBIRetry


def _read_timeout(cause_message: str) -> ReadTimeoutError:
    error = ReadTimeoutError(None, '/refreshes', 'Read timed out. (read timeout=10)')
    error.__cause__ = TimeoutError(cause_message)
    return error


class SilentTlsServer:
    """Accepts TCP connections but never answers the TLS handshake."""

    def __init__(self):
        self._socket = socket.create_server(('127.0.0.1', 0))
        self._connections = []
        self.port = self._socket.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def close(self):
        for connection in self._connections:
            connection.close()
        self._socket.close()

    def _accept(self):
        while True:
            try:
                connection, _ = self._socket.accept()
            except OSError:
                return
            self._connections.append(connection)


class TestPowerBIRetry(unittest.TestCase):
    def test_post_is_resent_after_tls_handshake_timeout(self):
        server = SilentTlsServer()
        self.addCleanup(server.close)
        session = requests.Session()
        session.mount('https://', HTTPAdapter(max_retries=PowerBIRetry(total=2, backoff_factor=0)))

        with self.assertRaises(requests.ConnectionError):
            session.post(f'https://127.0.0.1:{server.port}/refreshes', timeout=(0.2, 0.2))

        self.assertEqual(server.connection_count, 3)

    def test_tls_handshake_timeout_on_post_uses_a_connect_retry(self):
        retry = PowerBIRetry(total=5, connect=5)

        retry = retry.increment(
            method='POST', url='/refreshes', error=_read_timeout('_ssl.c:1018: The handshake operation timed out')
        )

        self.assertEqual(retry.connect, 4)

    def test_response_read_timeout_on_post_is_not_retried(self):
        # The request was sent, so resending it could start a second refresh.
        error = _read_timeout('The read operation timed out')

        with self.assertRaises(ReadTimeoutError):
            PowerBIRetry(total=5).increment(method='POST', url='/refreshes', error=error)


if __name__ == '__main__':
    unittest.main()
