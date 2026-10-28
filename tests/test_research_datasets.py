import pandas as pd
from openpyxl import Workbook

from eom_empirical.research_datasets import _parse_undesa_workbook
from eom_empirical.eurostat_api import parse_jsonstat_multi_geo_observations


def test_undesa_workbook_parses_country_stock_by_year_and_sex(tmp_path):
    path = tmp_path / "undesa.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Table 1"
    ws.append(["row_num", "country_name", "coverage", "data_type", "un_code"] + [None] * 24)
    spain = [1, "Spain", "Country", "Estimate", 724]
    spain += list(range(100, 108)) + list(range(200, 208)) + list(range(300, 308))
    aggregate = [2, "Europe", "Region", "Estimate", 900]
    aggregate += list(range(1000, 1008)) + list(range(2000, 2008)) + list(range(3000, 3008))
    ws.append(spain)
    ws.append(aggregate)
    wb.save(path)

    result = _parse_undesa_workbook(path, "destination", "test-run", {"spain": "ESP"})

    assert len(result) == 24
    assert result["country_code_un"].unique().tolist() == [724]
    assert result["country_code_iso3"].unique().tolist() == ["ESP"]
    total_1990 = result[(result["sex"] == "Total sexes") & (result["year"] == 1990)].iloc[0]
    male_2024 = result[(result["sex"] == "Male") & (result["year"] == 2024)].iloc[0]
    female_2020 = result[(result["sex"] == "Female") & (result["year"] == 2020)].iloc[0]
    assert total_1990["migrant_stock_persons"] == 100
    assert male_2024["migrant_stock_persons"] == 207
    assert female_2020["migrant_stock_persons"] == 306


def test_eurostat_multi_geo_parser_keeps_geo_year_keys_and_labels():
    payload = {
        "id": ["freq", "unit", "geo", "age", "agedef", "sex", "time"],
        "size": [1, 1, 2, 1, 1, 1, 2],
        "dimension": {
            "freq": {"category": {"index": {"A": 0}}},
            "unit": {"category": {"index": {"NR": 0}}},
            "geo": {
                "category": {
                    "index": {"ES": 0, "PT": 1},
                    "label": {"ES": "Spain", "PT": "Portugal"},
                }
            },
            "age": {"category": {"index": {"TOTAL": 0}}},
            "agedef": {"category": {"index": {"REACH": 0}}},
            "sex": {"category": {"index": {"T": 0}}},
            "time": {"category": {"index": {"2020": 0, "2021": 1}}},
        },
        "value": {"0": 123, "1": 145, "2": 99, "3": 102},
    }
    values, _flags, labels = parse_jsonstat_multi_geo_observations(
        payload, start_year=2020, end_year=2021
    )
    assert values == {
        ("ES", 2020): 123.0,
        ("ES", 2021): 145.0,
        ("PT", 2020): 99.0,
        ("PT", 2021): 102.0,
    }
    assert labels == {"ES": "Spain", "PT": "Portugal"}


def test_undesa_bilateral_workbook_parses_origin_destination_pairs(tmp_path):
    from eom_empirical.research_datasets import _parse_undesa_bilateral_workbook

    path = tmp_path / "undesa_bilateral.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Table 1"
    ws.append([
        "Index",
        "Region, development group, country or area of destination",
        "Coverage",
        "Data type",
        "Location code of destination",
        "Region, development group, country or area of origin",
        "Location code of origin",
    ] + [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024] * 3)
    pair = [1, "Spain", "Country", "Estimate", 724, "India", 356]
    pair += list(range(100, 108)) + list(range(200, 208)) + list(range(300, 308))
    aggregate = [2, "Europe", "Region", "Estimate", 900, "India", 356]
    aggregate += list(range(1000, 1008)) + list(range(2000, 2008)) + list(range(3000, 3008))
    ws.append(pair)
    ws.append(aggregate)
    wb.save(path)

    result = _parse_undesa_bilateral_workbook(
        path, "test-run", {"spain": "ESP", "india": "IND"}
    )

    assert len(result) == 24
    assert result["destination_code_un"].unique().tolist() == [724]
    assert result["origin_code_un"].unique().tolist() == [356]
    assert result["destination_code_iso3"].unique().tolist() == ["ESP"]
    assert result["origin_code_iso3"].unique().tolist() == ["IND"]
    both_1990 = result[(result["sex"] == "Total sexes") & (result["year"] == 1990)].iloc[0]
    male_2024 = result[(result["sex"] == "Male") & (result["year"] == 2024)].iloc[0]
    assert both_1990["migrant_stock_persons"] == 100
    assert male_2024["migrant_stock_persons"] == 207


def test_ilostat_focus_filter_retains_origin_breakdown_and_source_flags():
    from eom_empirical.research_datasets import filter_ilostat_focus

    source = pd.DataFrame([
        {
            "ref_area": "GBR",
            "ref_area.label": "United Kingdom",
            "indicator": "POP_XFRB_SEX_CBR_NB",
            "sex": "SEX_T",
            "classif1": "CBR_BRT_IND",
            "classif1.label": "Country of birth: India",
            "time": 2022,
            "obs_value": 123.4,
            "obs_status": "P",
            "source.label": "Labour force survey",
        },
        {
            "ref_area": "BRA",
            "ref_area.label": "Brazil",
            "indicator": "POP_XFRB_SEX_CBR_NB",
            "sex": "SEX_F",
            "classif1": "CBR_BRT_TOTAL",
            "classif1.label": "Country of birth: Total",
            "time": 2021,
            "obs_value": 56.7,
            "obs_status": "",
            "source.label": "National survey",
        },
        {
            "ref_area": "XYZ",
            "ref_area.label": "Non-focus area",
            "indicator": "POP_XFRB_SEX_CBR_NB",
            "sex": "SEX_T",
            "classif1": "CBR_BRT_TOTAL",
            "classif1.label": "Country of birth: Total",
            "time": 2020,
            "obs_value": 5.0,
            "obs_status": "",
            "source.label": "Source",
        },
    ])
    result = filter_ilostat_focus(source)
    assert result["ref_area"].tolist() == ["GBR", "BRA"]
    assert result.iloc[0]["classif1"] == "CBR_BRT_IND"
    assert result.iloc[0]["obs_status"] == "P"
    assert "source.label" in result.columns



def test_ilostat_fetch_uses_official_csv_endpoint_and_caps_year(tmp_path):
    from datetime import datetime, timezone

    from eom_empirical.research_datasets import (
        ILOSTAT_MIGRATION_INDICATORS,
        ILOSTAT_TOC_URL,
        fetch_ilostat_migration_focus,
    )

    query_end_year = datetime.now(timezone.utc).year - 1
    current_ids = {
        "POP_XFRB_SEX_CBR_NB": "POP_XFRB_SEX_CBR_NB_A",
        "EMP_XFRB_SEX_CBR_NB": "EMP_XFRB_SEX_CBR_NB_A",
        "POP_XFLB_SEX_CBR_NB": "POP_XFLB_SEX_CBR_NB_A",
    }

    class FakeResponse:
        def __init__(self, body, url):
            self.status_code = 200
            self.content = body.encode("utf-8")
            self.text = body
            self.url = url

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None, timeout=None):
            self.calls.append((url, dict(params or {}), timeout))
            if url == ILOSTAT_TOC_URL:
                rows = ["id,indicator.label,freq,freq.label"]
                for legacy_id, label in ILOSTAT_MIGRATION_INDICATORS.items():
                    rows.append(f"{current_ids[legacy_id]},{label},A,Annual")
                return FakeResponse("\n".join(rows) + "\n", url)
            dataset_id = params["id"]
            body = (
                "ref_area,ref_area.label,indicator,sex,classif1,time,obs_value,source\n"
                f"GBR,United Kingdom,{dataset_id},SEX_T,CBR_BRT_TOTAL,2020,123.4,LFS\n"
                f"GBR,United Kingdom,{dataset_id},SEX_T,CBR_BRT_TOTAL,{query_end_year},234.5,LFS\n"
                f"GBR,United Kingdom,{dataset_id},SEX_T,CBR_BRT_TOTAL,{query_end_year + 1},999.9,LFS\n"
            )
            return FakeResponse(body, url)

    session = FakeSession()
    fresh, statuses = fetch_ilostat_migration_focus(
        session, tmp_path, "test-run", 2010, query_end_year + 1
    )

    assert len(statuses) == len(ILOSTAT_MIGRATION_INDICATORS) == 3
    assert all(status["status"] == "SUCCESS" for status in statuses), statuses
    assert all(status["request_variant"] == "rplumber_csv_year_bounded" for status in statuses)
    assert all("id=" in status["url"] and "timefrom=2010" in status["url"] for status in statuses)
    assert all(status["observation_end_queried"] == query_end_year for status in statuses)
    assert {status["indicator_code"] for status in statuses} == set(current_ids.values())
    assert all(status["id_resolution"] == "official_catalogue_label_match" for status in statuses)
    assert len(session.calls) == 1 + len(ILOSTAT_MIGRATION_INDICATORS)
    assert session.calls[0][0] == ILOSTAT_TOC_URL
    assert all(call[0] == "https://rplumber.ilo.org/data/indicator" for call in session.calls[1:])
    assert all(call[1]["format"] == ".csv" for call in session.calls[1:])
    assert all(call[1]["timefrom"] == 2010 and call[1]["timeto"] == query_end_year for call in session.calls[1:])
    assert fresh["time"].max() == query_end_year
    assert (fresh["time"] < query_end_year + 1).all()
    assert set(fresh["ref_area"]) == {"GBR"}
    snapshot_dir = tmp_path / "data" / "raw" / "snapshots" / "ilostat" / "test-run"
    assert (snapshot_dir / "indicator_catalogue.csv").exists()
    for dataset_id in current_ids.values():
        assert (snapshot_dir / f"{dataset_id}.csv").exists()

def test_spain_policy_monitor_uses_current_official_portal():
    from scripts.refresh_eom_data import POLICY_URLS

    spain_rows = [row for row in POLICY_URLS if row[0] == "Spain"]
    assert len(spain_rows) == 1
    assert spain_rows[0][1] == "Ministry of Inclusion, Social Security and Migration news"
    assert spain_rows[0][2] == "https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/inclusion/Paginas/index.aspx"



def test_unhcr_export_is_preserved_as_raw_snapshot(tmp_path):
    import hashlib

    from eom_empirical.research_datasets import UNHCR_EXPORT_URL, fetch_unhcr_focus

    body = (
        "time_period,ref_area_adm0,area_ori_adm0,obs_value,record_id\n"
        "2024,SGP,IND,123,rec1\n"
    ).encode("utf-8")

    class FakeResponse:
        headers = {"Content-Type": "text/csv"}
        url = UNHCR_EXPORT_URL

        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024 * 1024):
            yield self.content

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeSession:
        def get(self, url, headers=None, timeout=None, stream=False):
            assert url == UNHCR_EXPORT_URL
            assert stream is True
            return FakeResponse(body)

    fresh, status = fetch_unhcr_focus(FakeSession(), tmp_path, "test-run")
    snapshot_path = tmp_path / status["raw_snapshot_path"]

    assert status["status"] == "SUCCESS", status
    assert status["source_rows"] == 1
    assert status["focus_rows"] == 1
    assert snapshot_path.exists()
    assert snapshot_path.read_bytes() == body
    assert status["sha256_full_export"] == hashlib.sha256(body).hexdigest()
    assert len(fresh) == 1


def test_oecd_migration_response_is_preserved_as_raw_snapshot(tmp_path):
    import hashlib

    from eom_empirical.research_datasets import OECD_MIGRATION_QUERY, fetch_oecd_migration_slice

    body = (
        "REF_AREA,TIME_PERIOD,OBS_VALUE\n"
        "GBR,2024,12\n"
    ).encode("utf-8")

    class FakeResponse:
        def __init__(self, content, url):
            self.content = content
            self.text = content.decode("utf-8")
            self.url = url

        def raise_for_status(self):
            return None

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            assert url == OECD_MIGRATION_QUERY
            return FakeResponse(body, url)

    fresh, status = fetch_oecd_migration_slice(FakeSession(), tmp_path, "test-run", 2010, 2025)
    snapshot_path = tmp_path / status["raw_snapshot_path"]

    assert status["status"] == "SUCCESS", status
    assert "startPeriod=2010" in status["url"]
    assert "dimensionAtObservation=AllDimensions" in status["url"]
    assert len(fresh) == 1
    assert snapshot_path.exists()
    assert snapshot_path.read_bytes() == body
    assert status["sha256_response"] == hashlib.sha256(body).hexdigest()
