#!/usr/bin/env python3
"""Versioned ingestion of OECD International Migration Outlook 2026 A-series StatLinks."""
from __future__ import annotations
import argparse, gzip, hashlib, json, re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = "Organisation for Economic Co-operation and Development (OECD)"
RELEASE_DATE = "2026-11-12"
SOURCE_PAGE = "https://www.oecd.org/en/publications/international-migration-outlook-2026_a9eab36b-en/full-report/statistical-annex_f79de055.html"
STATLINKS = {
    "A.1": "https://stat.link/kr1oyp",
    "A.3": "https://stat.link/pj3a4w",
    "A.4": "https://stat.link/2d1v8s",
    "A.5": "https://stat.link/qz4crd",
    "A.6": "https://stat.link/zmq54t",
}
BASE_MEASURES = {
    "A.1": ("immigration_foreign_population", "thousands"),
    "A.3": ("new_asylum_requests", "persons"),
    "A.4": ("foreign_born_population_stock", "thousands"),
    "A.5": ("foreign_population_stock_by_nationality", "thousands"),
    "A.6": ("acquisitions_of_nationality", "persons"),
}
NATURAL_KEYS = ["table_code", "destination", "origin", "measure", "year"]
OUTPUT_COLUMNS = [
    "table_code", "table_heading", "destination", "origin", "measure", "year",
    "value", "raw_value", "unit", "observation_status", "missing_marker",
    "publisher", "source_url", "source_permalink", "source_page", "release_date",
    "source_vintage", "source_version", "source_sheet", "retrieved_at_utc",
    "run_id", "raw_snapshot_sha256",
]

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_numeric(raw: Any):
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None, "missing", ""
    text = str(raw).replace("\xa0", " ").strip()
    if text in {"", "..", ".", "…", "—", "–", "-"}:
        return None, "missing", text or "blank"
    try:
        return float(text.replace(" ", "").replace(",", "")), "observed", ""
    except ValueError:
        return None, "unparsed", text

def extract_release_metadata(raw: bytes) -> tuple[str, str]:
    book = pd.ExcelFile(BytesIO(raw), engine="openpyxl")
    if "About this file" not in book.sheet_names:
        return RELEASE_DATE, "unknown"
    about = pd.read_excel(BytesIO(raw), sheet_name="About this file", header=None, engine="openpyxl")
    text = " ".join(str(x) for x in about.to_numpy().ravel() if pd.notna(x))
    version_match = re.search(r"Version\s+([^\s-]+)", text, flags=re.I)
    date_match = re.search(r"Last updated:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", text, flags=re.I)
    release = datetime.strptime(date_match.group(1), "%d-%b-%Y").date().isoformat() if date_match else RELEASE_DATE
    version = version_match.group(1) if version_match else "unknown"
    return release, version

def parse_statlink_workbook(raw: bytes, short_url: str, final_url: str,
                            retrieved_at: str, run_id: str, digest: str) -> tuple[pd.DataFrame, dict]:
    book = pd.ExcelFile(BytesIO(raw), engine="openpyxl")
    sheet_name = next((s for s in book.sheet_names if re.match(r"A[1-6]_EN_2026", s)), None)
    if sheet_name is None:
        raise ValueError(f"No A-series data sheet found in workbook: {book.sheet_names}")
    frame = pd.read_excel(BytesIO(raw), sheet_name=sheet_name, header=None, engine="openpyxl")
    title = str(frame.iloc[0, 0]).replace("\xa0", " ").strip()
    match = re.search(r"Table\s*(A\.\d+)", title)
    if not match:
        raise ValueError(f"Cannot identify table code from workbook title: {title}")
    code = match.group(1)
    if code not in BASE_MEASURES:
        raise ValueError(f"Unexpected OECD table code in workbook: {code}")
    header_idx = None
    year_columns = []
    for i in range(min(8, len(frame))):
        candidate = []
        for j, cell in enumerate(frame.iloc[i].tolist()):
            try:
                year = int(float(cell))
                if 1900 <= year <= 2100 and j > 0:
                    candidate.append((j, year))
            except (TypeError, ValueError, OverflowError):
                continue
        if len(candidate) >= 5:
            header_idx, year_columns = i, candidate
            break
    if header_idx is None:
        raise ValueError(f"Could not find year header row in {sheet_name}")
    release_date, version = extract_release_metadata(raw)
    base_measure, base_unit = BASE_MEASURES[code]
    rows = []
    previous_entity = ""
    for i in range(header_idx + 1, len(frame)):
        label_cell = frame.iloc[i, 0]
        if pd.isna(label_cell) or not str(label_cell).strip():
            continue
        label = str(label_cell).replace("\xa0", " ").strip()
        if label.casefold().startswith("note:"):
            break
        low = label.casefold()
        if low.lstrip("%").strip().startswith("of total population"):
            if code == "A.4":
                measure, unit, entity = "foreign_born_population_share", "percent", previous_entity
            elif code == "A.5":
                measure, unit, entity = "foreign_population_share", "percent", previous_entity
            else:
                measure, unit, entity = base_measure, base_unit, label
        elif low.startswith("% of foreign population") and code == "A.6":
            measure, unit, entity = "acquisitions_share_of_foreign_population", "percent", previous_entity
        else:
            measure, unit, entity = base_measure, base_unit, label
            previous_entity = label
        for col_idx, year in year_columns:
            raw_value = frame.iloc[i, col_idx]
            value, status, marker = parse_numeric(raw_value)
            rows.append({
                "table_code": code, "table_heading": title, "destination": entity,
                "origin": "", "measure": measure, "year": year, "value": value,
                "raw_value": "" if pd.isna(raw_value) else str(raw_value).strip(),
                "unit": unit, "observation_status": status, "missing_marker": marker,
                "publisher": PUBLISHER, "source_url": final_url,
                "source_permalink": short_url, "source_page": SOURCE_PAGE,
                "release_date": release_date, "source_vintage": f"IMO2026-{release_date}",
                "source_version": version, "source_sheet": sheet_name,
                "retrieved_at_utc": retrieved_at, "run_id": run_id,
                "raw_snapshot_sha256": digest,
            })
    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if out.empty:
        raise ValueError(f"No observations parsed from {sheet_name}")
    duplicates = int(out.duplicated(NATURAL_KEYS).sum())
    if duplicates:
        conflicts = out.groupby(NATURAL_KEYS, dropna=False)["raw_value"].nunique()
        if len(conflicts[conflicts > 1]):
            raise ValueError(f"Conflicting duplicate natural keys in {code}")
        out = out.drop_duplicates(NATURAL_KEYS, keep="first")
    audit = {
        "table_code": code, "table_heading": title, "sheet_name": sheet_name,
        "release_date": release_date, "source_version": version,
        "observation_start": int(out.year.min()), "observation_end": int(out.year.max()),
        "destinations": sorted(x for x in out.destination.dropna().unique() if x),
        "destination_count": int(out.destination.nunique()),
        "rows_fetched": int(len(out)), "numeric_rows": int(out.value.notna().sum()),
        "missing_rows": int(out.value.isna().sum()),
        "unparsed_rows": int((out.observation_status == "unparsed").sum()),
        "duplicate_natural_keys_rejected": duplicates,
        "natural_key_columns": NATURAL_KEYS,
        "unit_counts": {str(k): int(v) for k, v in out.groupby("unit").size().items()},
        "raw_snapshot_sha256": digest, "raw_snapshot_bytes": len(raw),
        "source_url": final_url, "source_permalink": short_url,
    }
    return out, audit

def append_revision_history(current: pd.DataFrame, history_path: Path) -> dict:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(history_path, dtype={"raw_value": "string"}) if history_path.exists() else pd.DataFrame(columns=OUTPUT_COLUMNS)
    if old.empty:
        latest = old
    else:
        old["retrieved_at_utc"] = pd.to_datetime(old["retrieved_at_utc"], errors="coerce", utc=True)
        latest = old.sort_values("retrieved_at_utc", kind="stable").drop_duplicates(NATURAL_KEYS, keep="last")
    index = {tuple(row[k] if pd.notna(row[k]) else "" for k in NATURAL_KEYS): row for _, row in latest.iterrows()}
    additions = []
    inserted = revised = unchanged = 0
    for _, row in current.iterrows():
        key = tuple(row[k] if pd.notna(row[k]) else "" for k in NATURAL_KEYS)
        prior = index.get(key)
        if prior is None:
            additions.append(row.to_dict()); inserted += 1; continue
        old_value = None if pd.isna(prior.get("value")) else float(prior.get("value"))
        new_value = None if pd.isna(row.get("value")) else float(row.get("value"))
        same = (old_value == new_value and str(prior.get("raw_value", "")) == str(row.get("raw_value", "")) and
                str(prior.get("observation_status", "")) == str(row.get("observation_status", "")))
        if same:
            unchanged += 1
        else:
            additions.append(row.to_dict()); revised += 1
    if additions:
        history = pd.concat([old, pd.DataFrame(additions)], ignore_index=True)
        history.to_csv(history_path, index=False)
    else:
        history = old
        if not history_path.exists():
            history.to_csv(history_path, index=False)
    return {
        "inserted_new_natural_keys": inserted, "appended_value_revisions": revised,
        "unchanged_keys_skipped": unchanged, "history_rows_after": int(len(history)),
        "history_unique_natural_keys": int(history[NATURAL_KEYS].drop_duplicates().shape[0]) if not history.empty else 0,
    }

def run(run_id: str | None = None) -> dict:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    retrieved_at = utc_now()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EOM-Research-ETL/1.0; +https://github.com/schnozenstein/eom-migration-model)",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*",
    }
    snapshot_dir = ROOT / "data" / "raw" / "snapshots" / "oecd_imo_2026" / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    extracts, source_audits = [], []
    for expected_code, short_url in STATLINKS.items():
        response = requests.get(short_url, timeout=(15, 90), headers=headers, allow_redirects=True)
        response.raise_for_status()
        raw = response.content
        if not raw.startswith(b"PK"):
            raise ValueError(f"OECD StatLink {short_url} did not return an XLSX payload")
        digest = sha256_bytes(raw)
        raw_path = snapshot_dir / f"statlink_{expected_code.replace('.', '')}.xlsx"
        raw_path.write_bytes(raw)
        parsed, audit = parse_statlink_workbook(raw, short_url, response.url, retrieved_at, run_id, digest)
        if audit["table_code"] != expected_code:
            raise ValueError(f"Expected {expected_code}, received {audit['table_code']} from {short_url}")
        audit.update({"http_status": response.status_code, "status": "SUCCESS",
                      "raw_snapshot_path": str(raw_path.relative_to(ROOT)),
                      "retrieved_at_utc": retrieved_at})
        extracts.append(parsed)
        source_audits.append(audit)

    current = pd.concat(extracts, ignore_index=True)
    duplicate_count = int(current.duplicated(NATURAL_KEYS).sum())
    if duplicate_count:
        raise ValueError(f"Cross-workbook duplicate natural keys detected: {duplicate_count}")
    current = current.sort_values(NATURAL_KEYS, kind="stable").reset_index(drop=True)

    current_dir = ROOT / "data" / "derived" / "oecd_imo_2026"
    current_dir.mkdir(parents=True, exist_ok=True)
    current_path = current_dir / f"a_series_long_{run_id}.csv"
    current.to_csv(current_path, index=False)
    history_path = ROOT / "data" / "observations_history" / "oecd_imo_2026_a_series_history.csv"
    history_stats = append_revision_history(current, history_path)

    metadata_dir = ROOT / "metadata" / "oecd_imo_2026"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    source_audit_path = metadata_dir / f"a_series_source_audit_{run_id}.csv"
    pd.DataFrame(source_audits).to_csv(source_audit_path, index=False)
    manifest = {
        "run_id": run_id, "publisher": PUBLISHER, "source_page": SOURCE_PAGE,
        "release_date": RELEASE_DATE, "retrieved_at_utc": retrieved_at,
        "source_status": "SUCCESS", "tables_expected": sorted(STATLINKS),
        "tables_parsed": sorted(current.table_code.unique().tolist()),
        "rows_fetched": int(len(current)), "numeric_rows": int(current.value.notna().sum()),
        "missing_rows": int(current.value.isna().sum()),
        "unparsed_rows": int((current.observation_status == "unparsed").sum()),
        "duplicate_natural_keys_rejected": duplicate_count,
        "observation_start": int(current.year.min()), "observation_end": int(current.year.max()),
        "destinations_by_table": {k: sorted(v) for k, v in current.groupby("table_code").destination.unique().items()},
        "rows_by_table": {str(k): int(v) for k, v in current.groupby("table_code").size().items()},
        "missing_by_table": {str(k): int(v) for k, v in current[current.value.isna()].groupby("table_code").size().items()},
        "natural_key_columns": NATURAL_KEYS,
        "source_retrieval_audit": source_audits,
        "current_extract_path": str(current_path.relative_to(ROOT)),
        "history_path": str(history_path.relative_to(ROOT)),
        "source_audit_path": str(source_audit_path.relative_to(ROOT)),
        "comparability_warning": "OECD national definitions differ. A-series destination totals are not bilateral OD flows. Stock, asylum, immigration and naturalisation measures remain separate.",
        "not_ingested_yet": ["A.2", "B.1", "B.3", "B.4", "B.5", "B.6"],
        **history_stats,
    }
    manifest_path = metadata_dir / f"a_series_manifest_{run_id}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path = ROOT / "reports" / f"oecd_imo_2026_a_series_{run_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = (
        "# OECD International Migration Outlook 2026 — A-series StatLink ingestion\n\n"
        f"- Run: {run_id}\n- Release date: {RELEASE_DATE}\n- Retrieved: {retrieved_at}\n"
        f"- Tables parsed: {', '.join(manifest['tables_parsed'])}\n"
        f"- Observation rows: {len(current):,}\n- Numeric rows: {manifest['numeric_rows']:,}\n"
        f"- Missing rows preserved: {manifest['missing_rows']:,}\n"
        f"- Duplicate natural keys: {duplicate_count}\n"
        f"- New keys: {history_stats['inserted_new_natural_keys']:,}\n"
        f"- Revisions appended: {history_stats['appended_value_revisions']:,}\n"
        f"- Unchanged keys skipped: {history_stats['unchanged_keys_skipped']:,}\n\n"
        "## Table coverage\n\n"
        "| Table | Definition | Unit | Rows | Missing |\n|---|---|---:|---:|---:|\n"
        + "\n".join(
            f"| {a['table_code']} | {a['table_heading']} | {', '.join(a['unit_counts'])} | {a['rows_fetched']} | {a['missing_rows']} |"
            for a in source_audits
        )
        + "\n\n## Interpretation safeguards\n\n"
        "- A.1 immigration, A.3 asylum applications, A.4/A.5 population stocks and A.6 nationality acquisitions are separate outcomes.\n"
        "- Units are preserved by table; thousands are not mixed with persons or percentages.\n"
        "- Missing markers are preserved as missing, never converted to zero.\n"
        "- These destination-level A-series tables are not origin-destination flows.\n"
        "- No EOM energy, ranking, parameter calibration or causal estimate was changed.\n"
        "- Remaining tables A.2 and B.1/B.3/B.4/B.5/B.6 require separate retrieval/normalisation.\n"
    )
    report_path.write_text(report, encoding="utf-8")
    manifest.update({"manifest_path": str(manifest_path.relative_to(ROOT)),
                     "report_path": str(report_path.relative_to(ROOT))})
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.run_id), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
