#!/usr/bin/env python3
"""One-time reconstruction of compact WDI history from a prior ETL artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

from refresh_eom_data import ROOT, WB_API_CODE_OVERRIDES, atomic_csv, compact_wdi_history, stable_wdi_country_key


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def rebuild(input_root: Path, output_path: Path, source_artifact_run_id: str,
            source_artifact_name: str, source_artifact_digest: str,
            rebuild_workflow_run_id: str) -> dict:
    input_root = input_root.resolve()
    if not (input_root / "data" / "raw" / "snapshots" / "world_bank").exists():
        candidates = sorted(
            path for path in input_root.rglob("world_bank")
            if path.is_dir()
            and path.parent.name == "snapshots"
            and path.parent.parent.name == "raw"
            and path.parent.parent.parent.name == "data"
        )
        if not candidates:
            raise RuntimeError(f"No World Bank raw snapshot directory found under downloaded artifact root {input_root}")
        input_root = candidates[0].parents[3]
    legacy_history_path = input_root / "data" / "observations_history" / "world_bank_observations.csv"
    legacy_rows = 0
    url_time_map = {}
    codes_by_run = {}
    if legacy_history_path.exists():
        with legacy_history_path.open("rb") as handle:
            legacy_rows = max(0, sum(1 for _ in handle) - 1)
        meta = pd.read_csv(legacy_history_path, usecols=["run_id", "indicator_code", "source_url", "retrieved_utc"], low_memory=False)
        meta["run_id"] = meta["run_id"].astype(str)
        meta["indicator_code"] = meta["indicator_code"].astype(str)
        for (run_id, code), group in meta.groupby(["run_id", "indicator_code"], dropna=False):
            url_time_map[(run_id, code)] = {
                "source_url": str(group["source_url"].dropna().iloc[0]) if group["source_url"].notna().any() else "",
                "retrieved_utc": str(group["retrieved_utc"].dropna().min()) if group["retrieved_utc"].notna().any() else "",
            }
            codes_by_run.setdefault(run_id, set()).add(code)

    run_meta_map = {}
    for path in sorted((input_root / "metadata" / "refresh_runs").glob("*.json")):
        data = _load_json(path)
        run_meta_map[str(data.get("run_id") or path.stem)] = data

    snapshot_root = input_root / "data" / "raw" / "snapshots" / "world_bank"
    run_dirs = sorted(path for path in snapshot_root.iterdir() if path.is_dir()) if snapshot_root.exists() else []
    if not run_dirs:
        raise RuntimeError(f"No World Bank raw snapshot directories found under {snapshot_root}")
    current_run_id = max(path.name for path in run_dirs)

    status_path = input_root / "metadata" / "live_source_status.csv"
    current_status_codes = set()
    if status_path.exists():
        try:
            status_df = pd.read_csv(status_path)
            if "indicator" in status_df:
                current_status_codes = set(status_df["indicator"].dropna().astype(str))
        except Exception:
            current_status_codes = set()

    observations = []
    snapshot_inventory = []
    for run_dir in run_dirs:
        run_id = run_dir.name
        run_meta = run_meta_map.get(run_id, {})
        run_time = str(run_meta.get("run_at_utc") or "")
        stem_to_code = {code.replace(".", "_"): code for code in codes_by_run.get(run_id, set())}
        if run_id == current_run_id:
            for code in current_status_codes:
                stem_to_code[code.replace(".", "_")] = code
        for snapshot in sorted(run_dir.glob("*_page_*.json")):
            stem = snapshot.name.rsplit("_page_", 1)[0]
            try:
                payload = json.loads(snapshot.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Invalid raw World Bank JSON snapshot {snapshot}: {exc}") from exc
            if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
                raise RuntimeError(f"Unexpected World Bank snapshot structure: {snapshot}")
            meta = payload[0]
            source_rows = payload[1] if isinstance(payload[1], list) else []
            if not source_rows:
                continue
            code = stem_to_code.get(stem)
            api_code = str(((source_rows[0].get("indicator") or {}).get("id")) or "")
            if not code:
                code = WB_API_CODE_OVERRIDES.get(api_code, api_code or stem.replace("_", "."))
            if not code:
                raise RuntimeError(f"Cannot resolve canonical indicator code for {snapshot}")
            vintage = url_time_map.get((run_id, code), {})
            retrieved_utc = str(vintage.get("retrieved_utc") or run_time)
            source_url = str(vintage.get("source_url") or "")
            if not source_url:
                params = {"date": "2010:2026", "format": "json", "per_page": 20000, "page": 1}
                source_url = f"https://api.worldbank.org/v2/country/all/indicator/{api_code}?{urlencode(params)}"
            snapshot_inventory.append({"run_id": run_id, "indicator_code": code, "file": snapshot.name, "rows": len(source_rows), "sha256": sha256_file(snapshot)})
            for item in source_rows:
                year_text = str(item.get("date") or "")
                if not year_text.isdigit():
                    continue
                country = item.get("country") or {}
                indicator = item.get("indicator") or {}
                region = country.get("region") or {}
                income = country.get("incomeLevel") or {}
                lending = country.get("lendingType") or {}
                source_geo_id = str(country.get("id") or "").strip().upper()
                country_code, country_code_type = stable_wdi_country_key(item.get("countryiso3code"), source_geo_id, region.get("id"), country.get("value"))
                value = item.get("value")
                observations.append({
                    "country_code": country_code, "country_code_type": country_code_type, "source_geo_id": source_geo_id,
                    "country_name_api": country.get("value"), "country_region_id": region.get("id"), "country_region_name": region.get("value"),
                    "income_level_id": income.get("id"), "income_level_name": income.get("value"), "lending_type_id": lending.get("id"),
                    "lending_type_name": lending.get("value"), "indicator_code": code, "indicator_api_code": indicator.get("id", api_code),
                    "indicator_name_api": indicator.get("value") or code, "year": int(year_text), "value": value,
                    "source": "World Bank Indicators API", "source_url": source_url, "retrieved_utc": retrieved_utc,
                    "run_id": run_id, "status": "observed" if value is not None else "missing", "api_lastupdated": str(meta.get("lastupdated") or ""),
                })

    raw = pd.DataFrame(observations)
    if raw.empty:
        raise RuntimeError("No World Bank observations were reconstructed from raw snapshots.")
    keys = ["country_code", "indicator_code", "year"]
    duplicate_keys_within_run = int(raw.duplicated(["run_id", *keys]).sum())
    if duplicate_keys_within_run:
        raise RuntimeError(f"Reconstructed WDI snapshots contain {duplicate_keys_within_run} duplicate run/natural-key rows.")
    ledger, _stats = compact_wdi_history(pd.DataFrame(), raw)
    output_path = output_path if output_path.is_absolute() else ROOT / output_path
    atomic_csv(ledger, output_path)
    current = raw[raw["run_id"].astype(str).eq(current_run_id)]
    ledger_counts = ledger.groupby(keys, dropna=False).size()
    restored_rows = int(len(raw) - legacy_rows)
    if restored_rows < 0:
        raise RuntimeError("Reconstructed raw snapshot count is lower than legacy history; refusing migration.")
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rebuild_workflow_run_id": str(rebuild_workflow_run_id),
        "source_artifact_run_id": str(source_artifact_run_id),
        "source_artifact_name": source_artifact_name,
        "source_artifact_digest": source_artifact_digest,
        "source_artifact_root": input_root.name,
        "source_snapshot_run_ids": [path.name for path in run_dirs],
        "source_snapshot_files": len(snapshot_inventory),
        "raw_snapshot_observation_rows": int(len(raw)),
        "legacy_history_rows": int(legacy_rows),
        "rows_restored_vs_legacy_history": restored_rows,
        "unique_observation_keys": int(raw[keys].drop_duplicates().shape[0]),
        "ledger_rows": int(len(ledger)),
        "duplicate_keys_within_run": duplicate_keys_within_run,
        "duplicate_version_keys": int(ledger.duplicated(["run_id", *keys]).sum()),
        "keys_with_multiple_versions": int((ledger_counts > 1).sum()),
        "extra_revision_rows": int((ledger_counts - 1).clip(lower=0).sum()),
        "current_run_id": current_run_id,
        "current_run_rows": int(len(current)),
        "current_run_indicator_count": int(current["indicator_code"].nunique()),
        "current_run_source_entity_count": int(current["country_code"].nunique()),
        "current_run_synthetic_source_id_rows": int(current["country_code_type"].eq("WB_SOURCE_ID").sum()),
        "current_run_missing_value_observations": int(current["value"].isna().sum()),
        "ledger_sha256": sha256_file(output_path),
        "snapshot_hashes": snapshot_inventory,
        "note": "One-time migration rebuilt normalized observations from raw source snapshots because the legacy blank-ISO3 natural key collapsed distinct World Bank aggregates. Unchanged observation values are stored once; only later revisions are retained.",
    }
    manifest_path = ROOT / "metadata" / "wdi_history_rebuild_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-artifact-run-id", default="")
    parser.add_argument("--source-artifact-name", default="")
    parser.add_argument("--source-artifact-digest", default="")
    parser.add_argument("--rebuild-workflow-run-id", default="")
    args = parser.parse_args()
    manifest = rebuild(args.input_root, args.output, args.source_artifact_run_id, args.source_artifact_name, args.source_artifact_digest, args.rebuild_workflow_run_id)
    print(json.dumps({k: manifest[k] for k in [
        "source_artifact_run_id", "source_snapshot_files", "raw_snapshot_observation_rows",
        "legacy_history_rows", "rows_restored_vs_legacy_history", "unique_observation_keys",
        "ledger_rows", "duplicate_keys_within_run", "keys_with_multiple_versions",
        "current_run_indicator_count", "current_run_source_entity_count",
        "current_run_synthetic_source_id_rows", "current_run_missing_value_observations", "ledger_sha256",
    ]}, indent=2))


if __name__ == "__main__":
    main()
