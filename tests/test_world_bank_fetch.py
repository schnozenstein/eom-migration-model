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



def test_fetch_indicator_splits_large_country_lists_into_bounded_requests():
    class FakeResponse:
        def __init__(self, url, codes):
            self.url = url
            self.codes = codes

        def raise_for_status(self):
            return None

        def json(self):
            observations = []
            for code in self.codes:
                observations.append({
                    "countryiso3code": code,
                    "country": {"value": code},
                    "indicator": {"id": "SL.UEM.TOTL.ZS", "value": "Unemployment"},
                    "date": "2025",
                    "value": 5.0,
                })
            return [{"pages": 1}, observations]

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None, timeout=None):
            country_path = url.split("/country/", 1)[1].split("/indicator/", 1)[0]
            codes = country_path.split(";")
            self.calls.append({"url": url, "params": params, "timeout": timeout, "codes": codes})
            return FakeResponse(url, codes)

    session = FakeSession()
    rows = wb.fetch_indicator(
        "USA;CAN;DEU;IRL;AUS",
        "SL.UEM.TOTL.ZS",
        2020,
        2025,
        timeout=25,
        session=session,
        country_chunk_size=2,
    )

    assert len(session.calls) == 3
    assert [len(call["codes"]) for call in session.calls] == [2, 2, 1]
    assert all(call["timeout"] == 25 for call in session.calls)
    assert {row["country_code"] for row in rows} == {"AUS", "CAN", "DEU", "IRL", "USA"}
    assert len(rows) == 5
