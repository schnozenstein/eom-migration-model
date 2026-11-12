import json

import pandas as pd
import pytest
import requests

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


def test_chunk_codes_splits_stably_and_deduplicates():
    codes = ["NLD", "DEU", "IND", "NLD", "AUS", "CAN", "JPN"]
    assert wb.chunk_codes(codes, size=3) == [
        ["AUS", "CAN", "DEU"],
        ["IND", "JPN", "NLD"],
    ]


def _payload(indicator, country, value):
    return [
        {"pages": 1, "lastupdated": "2026-11-11"},
        [{
            "countryiso3code": country,
            "country": {"value": country},
            "indicator": {"id": indicator, "value": wb.INDICATORS[indicator]},
            "date": "2024",
            "value": value,
        }],
    ]


def test_fetch_indicator_audited_chunks_countries_and_saves_raw_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(wb, "ROOT", tmp_path)
    monkeypatch.setattr(wb, "SNAPSHOT_ROOT", tmp_path / "data/raw/snapshots/world_bank/macro_focus")
    monkeypatch.setattr(wb.time, "sleep", lambda _delay: None)

    class Response:
        status_code = 200

        def __init__(self, url, country):
            self.url = url
            self.country = country
            self.content = json.dumps(_payload("NY.GDP.MKTP.PP.CD", country, 100.0)).encode()

        def raise_for_status(self):
            return None

        def json(self):
            return _payload("NY.GDP.MKTP.PP.CD", self.country, 100.0)

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None, timeout=None):
            self.calls.append((url, params, timeout))
            country = url.split("/country/")[1].split("/indicator/")[0].split(";")[0]
            return Response(url + "?date=2010%3A2024", country)

    session = FakeSession()
    codes = [f"C{i:02d}" for i in range(21)]
    rows, audit = wb.fetch_indicator_audited(
        codes, "NY.GDP.MKTP.PP.CD", 2010, 2024,
        session=session, snapshot_dir=tmp_path / "snapshots"
    )

    assert len(session.calls) == 3
    assert len(rows) == 3
    assert audit["fetch_status"] == "SUCCESS"
    assert len(json.loads(audit["request_urls_json"])) == 3
    assert len(json.loads(audit["raw_snapshot_paths_json"])) == 3
    assert all((tmp_path / p).exists() for p in json.loads(audit["raw_snapshot_paths_json"]))


def test_fetch_indicator_audited_retries_transient_502(tmp_path, monkeypatch):
    monkeypatch.setattr(wb, "ROOT", tmp_path)
    monkeypatch.setattr(wb.time, "sleep", lambda _delay: None)

    class Response:
        status_code = 200

        def __init__(self, url, status=200):
            self.url = url
            self.status = status
            self.content = b"{}"

        def raise_for_status(self):
            if self.status >= 400:
                raise requests.HTTPError(f"{self.status} Server Error")

        def json(self):
            return _payload("NY.GDP.MKTP.PP.CD", "AUS", 100.0)

    class FlakySession:
        def __init__(self):
            self.calls = 0

        def get(self, url, params=None, timeout=None):
            self.calls += 1
            if self.calls == 1:
                return Response(url, 502)
            return Response(url, 200)

    session = FlakySession()
    rows, audit = wb.fetch_indicator_audited(
        ["AUS"], "NY.GDP.MKTP.PP.CD", 2010, 2024,
        session=session, snapshot_dir=tmp_path / "snapshots"
    )
    assert session.calls == 2
    assert len(rows) == 1
    assert audit["fetch_status"] == "SUCCESS"


def test_append_macro_history_distinguishes_unchanged_vintages_from_value_revisions(tmp_path):
    path = tmp_path / "macro_history.csv.gz"
    base = pd.DataFrame([{
        "country_code": "AUS",
        "country_name_api": "Australia",
        "indicator_code": "NY.GDP.MKTP.PP.CD",
        "indicator_name_api": "GDP, PPP",
        "year": 2024,
        "value": 100.0,
        "unit": "indicator-defined",
        "source": "World Bank Indicators API",
        "source_url": "https://api.worldbank.org/v2/country/AUS/indicator/NY.GDP.MKTP.PP.CD",
        "source_vintage": "2026-10-08",
        "retrieved_utc": "2026-11-10T00:00:00Z",
    }])

    first = wb.append_macro_history(base, path)
    same = wb.append_macro_history(base.assign(retrieved_utc="2026-11-11T00:00:00Z"), path)
    new_vintage = wb.append_macro_history(
        base.assign(source_vintage="2026-11-11", retrieved_utc="2026-11-12T00:00:00Z"), path
    )
    value_revision = wb.append_macro_history(
        base.assign(source_vintage="2026-11-12", value=110.0, retrieved_utc="2026-11-13T00:00:00Z"), path
    )

    history = pd.read_csv(path, compression="gzip")
    assert first["inserted"] == 1
    assert same["unchanged"] == 1
    assert new_vintage["new_vintage_snapshots"] == 1
    assert value_revision["revised"] == 1
    assert len(history) == 3
    assert history.revision_type.tolist() == [
        "initial", "source_vintage_snapshot_unchanged", "value_revision"
    ]
