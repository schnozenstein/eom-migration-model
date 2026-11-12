import io
import zipfile
import pandas as pd

from eom_empirical.bilateral_gravity import (
    parse_jsonstat, orient_rows, iso2_to_iso3, append_history,
    prepare_panel, extract_geodist_workbook, write_geodist_blocked_outputs,
    MAIN_DATASET, CHECK_DATASET
)


def jsonstat_fixture():
    return {
        "id": ["geo", "partner", "time"],
        "size": [2, 2, 2],
        "dimension": {
            "geo": {"category": {"index": {"NL": 0, "UK": 1}}},
            "partner": {"category": {"index": {"DE": 0, "IN": 1}}},
            "time": {"category": {"index": {"2020": 0, "2021": 1}}}
        },
        "value": {"0": 12, "7": 0},
        "status": {"1": "c", "7": "p"}
    }


def test_jsonstat_sparse_parser_decodes_dimensions_and_flags():
    frame = parse_jsonstat(jsonstat_fixture(), MAIN_DATASET)
    row0 = frame.loc[frame.flat_index == 0].iloc[0]
    row7 = frame.loc[frame.flat_index == 7].iloc[0]
    assert (row0.geo, row0.partner, row0.time, row0.value) == ("NL", "DE", "2020", 12)
    assert (row7.geo, row7.partner, row7.time, row7.value) == ("UK", "IN", "2021", 0)
    assert row7.observation_status == "p"
    suppressed = frame.loc[frame.flat_index == 1].iloc[0]
    assert pd.isna(suppressed.value)
    assert suppressed.observation_status == "c"


def test_iso2_special_cases_and_aggregate_exclusion():
    assert iso2_to_iso3("EL") == "GRC"
    assert iso2_to_iso3("UK") == "GBR"
    assert iso2_to_iso3("IN") == "IND"
    assert iso2_to_iso3("EU27_2020") is None


def test_flow_orientation_is_directionally_consistent():
    raw = pd.DataFrame([{"geo":"NL","partner":"IN","time":"2020","value":100,"observation_status":""}])
    immigration = orient_rows(raw, MAIN_DATASET, "https://example.test/imm", "2026-11-07T00:00:00Z").iloc[0]
    emigration = orient_rows(raw, CHECK_DATASET, "https://example.test/emi", "2026-11-07T00:00:00Z").iloc[0]
    assert (immigration.origin_iso3, immigration.destination_iso3) == ("IND","NLD")
    assert (emigration.origin_iso3, emigration.destination_iso3) == ("NLD","IND")


def test_append_history_is_incremental_and_versions_revisions(tmp_path):
    path = tmp_path / "flows.csv.gz"
    base = pd.DataFrame([{
        "dataset": MAIN_DATASET, "measure":"immigration_previous_residence",
        "origin_iso3":"IND","destination_iso3":"NLD","year":2020,
        "flow_persons":100.0,"observation_status":"","source_flag":"",
        "unit":"NR","source_url":"https://example.test","publisher":"Eurostat",
        "retrieved_at_utc":"2026-11-07T00:00:00Z"
    }])
    first = append_history(base, path)
    second = append_history(base.assign(retrieved_at_utc="2026-11-08T00:00:00Z"), path)
    revised = append_history(base.assign(flow_persons=110.0,retrieved_at_utc="2026-11-09T00:00:00Z"), path)
    history = pd.read_csv(path, compression="gzip")
    assert first["inserted"] == 1
    assert second["unchanged"] == 1
    assert revised["revised"] == 1
    assert len(history) == 2
    assert sorted(history.revision_number.tolist()) == [1,2]
    assert float(history.iloc[-1].previous_value) == 100.0


def test_prepare_panel_uses_previous_year_features_and_eom_gap_sign():
    flows = pd.DataFrame([{
        "dataset":MAIN_DATASET,"measure":"immigration_previous_residence",
        "origin_iso3":"IND","destination_iso3":"NLD","year":2020,
        "flow_persons":100.0
    }])
    features = pd.DataFrame([
        {"country_iso3":"IND","year":2019,"gdp_pc_ppp":7000,"population":1.3e9,"eom_energy":3.0},
        {"country_iso3":"NLD","year":2019,"gdp_pc_ppp":50000,"population":1.7e7,"eom_energy":-2.0},
        # Current-year values must not enter the 2020 flow row.
        {"country_iso3":"IND","year":2020,"gdp_pc_ppp":99999,"population":1.3e9,"eom_energy":99.0},
        {"country_iso3":"NLD","year":2020,"gdp_pc_ppp":1,"population":1.7e7,"eom_energy":-99.0},
    ])
    geodist = pd.DataFrame([{
        "iso_o":"IND","iso_d":"NLD","distance_km":7000,"contig":0,"comlang_off":0
    }])
    panel = prepare_panel(flows, geodist, features).iloc[0]
    assert panel.feature_year == 2019
    assert panel.gdp_pc_origin == 7000
    assert panel.gdp_pc_destination == 50000
    assert panel.eom_attractor_gap == 5.0
    assert panel.eom_attractor_gap > 0



def test_extract_geodist_workbook_from_official_zip_member():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("CEPII/dist_cepii.xls", b"sample-workbook-bytes")
        archive.writestr("CEPII/geo_cepii.xls", b"country-workbook-bytes")
    member, workbook = extract_geodist_workbook(buffer.getvalue())
    assert member == "CEPII/dist_cepii.xls"
    assert workbook == b"sample-workbook-bytes"


def test_extract_geodist_workbook_rejects_missing_member():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("CEPII/geo_cepii.xls", b"country-workbook-bytes")
    try:
        extract_geodist_workbook(buffer.getvalue())
    except ValueError as exc:
        assert "Expected exactly one dist_cepii.xls" in str(exc)
    else:
        raise AssertionError("missing dyadic workbook should be rejected")



def test_cepii_source_failure_writes_blocked_status_and_archives_previous_result(tmp_path, monkeypatch):
    from eom_empirical import bilateral_gravity

    monkeypatch.setattr(bilateral_gravity, "ROOT", tmp_path)
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    previous = {
        "status": "completed_expanding_origin_bilateral_benchmark",
        "retrieval_run_id": "2026-11-07T112406Z",
        "gravity_ppml": {"n": 5196, "mae": 1714.05}
    }
    (output_dir / "bilateral_gravity_benchmark.json").write_text(
        __import__("json").dumps(previous), encoding="utf-8"
    )
    audit = {"run_id": "2026-11-08T054000Z", "sources": []}
    history = {"inserted": 3, "revised": 1, "unchanged": 5, "history_rows": 6000}
    reconciliation = {
        "matched_pair_years": 12,
        "correlation": 0.8,
        "median_absolute_difference_persons": 100.0,
        "median_absolute_percentage_difference": 10.0
    }
    reconciliation_rows = pd.DataFrame(columns=[
        "origin_iso3", "destination_iso3", "year",
        "immigration_reported_by_destination", "emigration_reported_by_origin"
    ])

    result = write_geodist_blocked_outputs(
        "2026-11-08T054000Z", audit, [], RuntimeError("403 Forbidden"),
        history, reconciliation, reconciliation_rows
    )

    current = __import__("json").loads(
        (output_dir / "bilateral_gravity_benchmark.json").read_text(encoding="utf-8")
    )
    archived = output_dir / "history" / "bilateral_gravity_benchmark_2026-11-07T112406Z.json"
    assert current["status"] == "blocked_geodist_source"
    assert current["rows_scored"] == 0
    assert current["previous_benchmark_archived"]["archived_path"] == str(
        archived.relative_to(tmp_path)
    )
    assert archived.exists()
    assert __import__("json").loads(archived.read_text())["gravity_ppml"]["n"] == 5196
    assert len(pd.read_csv(output_dir / "bilateral_gravity_benchmark_predictions.csv")) == 0
    assert "No PPML benchmark" in (
        tmp_path / "reports" / "bilateral_gravity_benchmark_latest.md"
    ).read_text()
    assert result["audit"]["status"] == "blocked_geodist_source"


def test_fetch_geodist_uses_hash_verified_prior_official_snapshot(tmp_path, monkeypatch):
    import hashlib
    import json
    import requests
    from eom_empirical import bilateral_gravity

    monkeypatch.setattr(bilateral_gravity, "ROOT", tmp_path)

    prior = tmp_path / "data/raw/snapshots/cepii_geodist/2026-11-11T234444Z"
    prior.mkdir(parents=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("CEPII/dist_cepii.xls", b"verified-workbook-bytes")
    zip_bytes = buffer.getvalue()
    zip_path = prior / "dist_cepii.zip"
    zip_path.write_bytes(zip_bytes)
    (prior / "cepii_snapshot_manifest.json").write_text(json.dumps({
        "publisher": "CEPII",
        "source_url": bilateral_gravity.CEPII_URL,
        "retrieved_at_utc": "2026-11-11T23:44:44Z",
        "sha256": hashlib.sha256(zip_bytes).hexdigest(),
        "source_artifact_run_id": "42913964349",
        "source_artifact_id": "13901197650",
        "source_artifact_digest": "sha256:verified",
    }))

    def forbidden(*args, **kwargs):
        raise requests.HTTPError("403 Forbidden")

    monkeypatch.setattr(bilateral_gravity.requests, "get", forbidden)
    monkeypatch.setattr(
        bilateral_gravity.pd,
        "read_excel",
        lambda *args, **kwargs: pd.DataFrame([{
            "iso_o": "IND", "iso_d": "NLD", "distw": 7000,
            "contig": 0, "comlang_off": 0
        }])
    )

    current = tmp_path / "data/raw/snapshots/cepii_geodist/2026-11-12T060000Z"
    frame, audit = bilateral_gravity.fetch_geodist(current)

    assert len(frame) == 1
    assert audit["status"] == "CARRIED_FORWARD_VERIFIED_OFFICIAL_SNAPSHOT"
    assert audit["carried_forward"] is True
    assert audit["attempted_current_download"]["status"] == "FAILED"
    assert "403 Forbidden" in audit["attempted_current_download"]["error"]
    assert (current / "dist_cepii.zip").exists()
    assert (current / "dist_cepii.xls").read_bytes() == b"verified-workbook-bytes"
    manifest = json.loads((current / "cepii_snapshot_manifest.json").read_text())
    assert manifest["carried_forward"] is True
    assert manifest["sha256"] == hashlib.sha256((current / "dist_cepii.zip").read_bytes()).hexdigest()
