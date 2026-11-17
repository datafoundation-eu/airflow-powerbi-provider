"""urllib3 retry policy for Power BI requests."""
from urllib3.exceptions import ReadTimeoutError
from urllib3.util.retry import Retry


class PowerBIRetry(Retry):
    """
    Retry policy that also retries a request whose TLS handshake timed out.

    urllib3 reports a TLS handshake timeout as a ``ReadTimeoutError``, so by
    default a POST is not retried after one. The handshake happens before the
    request is sent, so Power BI never received it and retrying cannot trigger a
    refresh twice. Such timeouts are treated as connection errors, which are
    retried for every method.
    """

    def _is_connection_error(self, err: Exception) -> bool:
        return super()._is_connection_error(err) or _is_tls_handshake_timeout(err)


def _is_tls_handshake_timeout(err: Exception) -> bool:
    # NOTE: CPython's ssl module gives a handshake timeout no type of its own; only the
    # message ("_ssl.c:1018: The handshake operation timed out") tells it apart from a
    # timeout while reading the response.
    return isinstance(err, ReadTimeoutError) and "handshake operation timed out" in str(err.__cause__)
