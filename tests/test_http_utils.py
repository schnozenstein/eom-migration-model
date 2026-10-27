import requests
import pytest

from eom_empirical.http_utils import get_with_retries


class _Response:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def close(self):
        self.closed = True


class _FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.closed = False

    def get(self, url, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def close(self):
        self.closed = True


def test_retries_connection_failures_then_succeeds(monkeypatch):
    monkeypatch.setattr("eom_empirical.http_utils.time.sleep", lambda _delay: None)
    expected = _Response()
    session = _FakeSession([
        requests.exceptions.ConnectionError("temporary DNS failure"),
        requests.exceptions.Timeout("socket timeout"),
        expected,
    ])

    result = get_with_retries(
        "https://example.test/api", session=session, attempts=3, base_delay=0
    )

    assert result is expected
    assert session.calls == 3


def test_retries_transient_http_status(monkeypatch):
    monkeypatch.setattr("eom_empirical.http_utils.time.sleep", lambda _delay: None)
    transient = _Response(503)
    expected = _Response(200)
    session = _FakeSession([transient, expected])

    result = get_with_retries(
        "https://example.test/api", session=session, attempts=2, base_delay=0
    )

    assert result is expected
    assert transient.closed
    assert session.calls == 2


def test_does_not_retry_tls_certificate_errors(monkeypatch):
    monkeypatch.setattr("eom_empirical.http_utils.time.sleep", lambda _delay: None)
    session = _FakeSession([
        requests.exceptions.SSLError("certificate verify failed"),
        _Response(200),
    ])

    with pytest.raises(requests.exceptions.SSLError):
        get_with_retries(
            "https://example.test/api", session=session, attempts=3, base_delay=0
        )

    assert session.calls == 1


def test_rejects_invalid_attempt_count():
    with pytest.raises(ValueError, match="attempts"):
        get_with_retries("https://example.test/api", attempts=0)
