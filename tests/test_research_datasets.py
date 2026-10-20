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
    ws.append(["row_num", "destination", "destination_code", "origin", "origin_code"] + [None] * 24)
    pair = [1, "Spain", 724, "India", 356]
    pair += list(range(100, 108)) + list(range(200, 208)) + list(range(300, 308))
    aggregate = [2, "Europe", 900, "India", 356]
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



def test_ilostat_fetch_resolves_current_annual_ids_retries_format_and_caps_year(tmp_path):
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
        def __init__(self, status_code, body, url):
            self.status_code = status_code
            self.text = body
            self.content = body.encode("utf-8")
            self.url = url

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"fake HTTP {self.status_code}")

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, params, timeout):
            self.calls.append((url, dict(params), timeout))
            if url == ILOSTAT_TOC_URL:
                rows = ["id,indicator.label,freq,freq.label"]
                for legacy_id, label in ILOSTAT_MIGRATION_INDICATORS.items():
                    rows.append(f"{current_ids[legacy_id]},{label},A,Annual")
                return FakeResponse(200, "\n".join(rows) + "\n", url)

            if params.get("format") == ".csv":
                return FakeResponse(400, "invalid CSV format token", url)

            dataset_id = params["id"]
            body = (
                "ref_area,ref_area.label,indicator,sex,classif1,time,obs_value,source\n"
                f"GBR,United Kingdom,{dataset_id},SEX_T,CBR_BRT_TOTAL,2020,123.4,LFS\n"
                f"GBR,United Kingdom,{dataset_id},SEX_T,CBR_BRT_TOTAL,{query_end_year},234.5,LFS\n"
                f"GBR,United Kingdom,{dataset_id},SEX_T,CBR_BRT_TOTAL,{query_end_year + 1},999.9,LFS\n"
            )
            return FakeResponse(200, body, url)

    session = FakeSession()
    fresh, statuses = fetch_ilostat_migration_focus(
        session, tmp_path, "test-run", 2010, query_end_year + 1
    )

    assert len(statuses) == len(ILOSTAT_MIGRATION_INDICATORS) == 3
    assert all(status["status"] == "SUCCESS" for status in statuses)
    assert all(status["request_variant"] == "bounded_csv" for status in statuses)
    assert all(status["observation_end_queried"] == query_end_year for status in statuses)
    assert {status["indicator_code"] for status in statuses} == set(current_ids.values())
    assert all(status["id_resolution"] == "official_catalogue_label_match" for status in statuses)
    assert len(session.calls) == 1 + 2 * len(ILOSTAT_MIGRATION_INDICATORS)
    assert session.calls[0][0] == ILOSTAT_TOC_URL
    assert all(call[1].get("timeto") == query_end_year for call in session.calls[1::2])
    assert fresh["time"].max() == query_end_year
    assert (fresh["time"] < query_end_year + 1).all()
    assert set(fresh["ref_area"]) == {"GBR"}

def test_spain_policy_monitor_uses_current_official_portal():
    from scripts.refresh_eom_data import POLICY_URLS

    spain_rows = [row for row in POLICY_URLS if row[0] == "Spain"]
    assert len(spain_rows) == 1
    assert spain_rows[0][1] == "Ministry of Inclusion, Social Security and Migration news"
    assert spain_rows[0][2] == "https://inclusion.gob.es/comunicacion/noticias"
