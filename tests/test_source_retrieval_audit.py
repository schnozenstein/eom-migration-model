import pandas as pd

from scripts import build_source_retrieval_audit as audit


def test_failed_source_rows_are_reported_as_carried_forward_not_fresh():
    prior = pd.DataFrame({"value": [10, 20, 30]})
    current, carried = audit.audit_current_rows(prior, "FAILED")
    assert current.empty
    assert carried == 3

    current, carried = audit.audit_current_rows(prior, "SUCCESS", "200")
    assert len(current) == 3
    assert carried == 0


def test_snapshot_lookup_is_limited_to_current_run_and_matching_source(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    old_run = tmp_path / "data/raw/snapshots/undesa/2026-11-07T055101Z"
    current_run = tmp_path / "data/raw/snapshots/undesa/2026-11-08T060343Z"
    old_run.mkdir(parents=True)
    current_run.mkdir(parents=True)
    (old_run / "undesa_pd_2024_ims_stock_by_sex_and_destination.xlsx").write_bytes(b"old destination")
    bilateral = current_run / "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx"
    bilateral.write_bytes(b"current bilateral")

    assert audit.snapshot_for(
        "undesa", ["by_sex_and_destination"], run_id="2026-11-08T060343Z"
    ) is None
    assert audit.snapshot_for(
        "undesa", ["destination_and_origin"], run_id="2026-11-08T060343Z"
    ) == bilateral
