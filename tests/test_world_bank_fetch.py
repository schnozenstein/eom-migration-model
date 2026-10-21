import requests
import pytest

from eom_empirical import fetch_world_bank as wb


def test_get_with_dns_retries_recovers_from_transient_dns_error(monkeypatch):
    monkeypatch.setattr(wb.time, "sleep", lambda _delay: None)
    expected_response = object()

    class FlakySession:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise requests.exceptions.ConnectionError(
                    "HTTPSConnectionPool: Temporary failure in name resolution"
                )
            return expected_response

    session = FlakySession()
    result = wb.get_with_dns_retries(
        session, "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"
    )

    assert result is expected_response
    assert session.calls == 2


def test_get_with_dns_retries_does_not_retry_non_dns_connection_error(monkeypatch):
    monkeypatch.setattr(wb.time, "sleep", lambda _delay: None)

    class RefusedSession:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            raise requests.exceptions.ConnectionError("Connection refused")

    session = RefusedSession()
    with pytest.raises(requests.exceptions.ConnectionError, match="Connection refused"):
        wb.get_with_dns_retries(session, "https://api.worldbank.org/v2/country/all")

    assert session.calls == 1
