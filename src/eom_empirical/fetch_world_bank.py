"""Fetch and version the registered-country World Bank macro-focus panel.

The request is chunked by country to reduce 502/504 failures. Raw JSON snapshots,
per-indicator retrieval metadata and an append-only source-vintage history are kept
separate from the current normalized model input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
DESTINATIONS = ROOT / "data" / "destinations.csv"
OUT = ROOT / "data" / "raw" / "world_bank_macro_focus.csv"
STATUS_OUT = ROOT / "metadata" / "macro_focus_source_status.csv"
MANIFEST_OUT = ROOT / "metadata" / "macro_focus_history_manifest.json"
HISTORY = ROOT / "data" / "observations_history" / "world_bank_macro_focus_observations.csv.gz"
SNAPSHOT_ROOT = ROOT / "data" / "raw" / "snapshots" / "world_bank" / "macro_focus"
CHUNK_SIZE = 10
CHUNK_ATTEMPTS = 4

INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant 2021 international $)",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current international $)",
    "PA.NUS.PPP": "PPP conversion factor, GDP (LCU per international $)",
    "PA.NUS.PRVT.PP": "PPP conversion factor, household/private consumption (LCU per international $)",
    "PA.NUS.PRVT.PLI": "Price level index (households and NPISHs final consumption expenditure; US=100)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force, ILO modeled estimate)",
    "GOV_WGI_RQ_EST": "Regulatory quality governance estimate (Worldwide Governance Indicators 2026 revision)",
    "GOV_WGI_GE_EST": "Government effectiveness governance estimate (Worldwide Governance Indicators 2026 revision)",
    "GOV_WGI_PV_EST": "Political stability governance estimate (Worldwide Governance Indicators 2026 revision)",
    "SP.POP.TOTL": "Population, total",
    "SM.POP.NETM": "Net migration",
}
BASE_URL = "https://api.worldbank.org/v2"
HISTORY_COLUMNS = [
    "country_code", "country_name_api", "indicator_code", "indicator_name_api",
    "year", "value", "unit", "source", "source_url", "source_vintage",
    "retrieved_utc", "revision_number", "revision_type", "previous_value",
    "record_hash"
]

DNS_ERROR_MARKERS = (
    "temporary failure in name resolution", "name or service not known",
    "getaddrinfo failed", "failed to resolve", "nodename nor servname",
    "name resolution",
)


def build_http_session() -> requests.Session:
    """Retry transient HTTP status/read failures; DNS is retried explicitly below."""
    session = requests.Session()
    retry = Retry(
        total=3, connect=0, read=2, status=3, backoff_factor=0.75,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "EOM-Research-ETL/2.3 (+reproducible academic research)"
    })
    return session


def get_with_dns_retries(
    session: requests.Session, url: str, *, attempts: int = 4,
    base_delay: float = 1.0, **kwargs
):
    """Retry only transient DNS resolution failures with bounded exponential backoff."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last_error = None
    for attempt in range(attempts):
        try:
            return session.get(url, **kwargs)
        except (socket.gaierror, requests.exceptions.ConnectionError) as exc:
            message = str(exc).lower()
            is_dns_error = isinstance(exc, socket.gaierror) or any(
                marker in message for marker in DNS_ERROR_MARKERS
            )
            if not is_dns_error:
                raise
            last_error = exc
            if attempt + 1 < attempts:
                delay = min(base_delay * (2**attempt), 8.0) + random.uniform(0.0, 0.25)
                print(f"Transient DNS failure for {url} (attempt {attempt + 1}/{attempts}); retrying in {delay:.2f}s")
                time.sleep(delay)
    raise requests.exceptions.ConnectionError(
        f"DNS resolution failed for {url} after {attempts} attempts: {last_error}"
    ) from last_error


def chunk_codes(codes: str | list[str], size: int = CHUNK_SIZE) -> list[list[str]]:
    """Split a semicolon-delimited or iterable country list into stable API batches."""
    if size < 1:
        raise ValueError("size must be >= 1")
    items = codes.split(";") if isinstance(codes, str) else list(codes)
    items = sorted({str(code).strip() for code in items if str(code).strip()})
    return [items[i:i + size] for i in range(0, len(items), size)]


def _parse_payload(payload: list, indicator: str, resolved_url: str, retrieved: str,
                   source_vintage: str) -> list[dict]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
        raise ValueError(f"Unexpected API response for {indicator}: {payload!r}")
    observations = payload[1] or []
    if not isinstance(observations, list):
        raise ValueError(
            f"Unexpected observations payload for {indicator}: {type(observations).__name__}"
        )
    rows = []
    for item in observations:
        country = item.get("country") or {}
        indicator_meta = item.get("indicator") or {}
        rows.append({
            "country_code": (item.get("countryiso3code") or "").upper(),
            "country_name_api": country.get("value"),
            "indicator_code": indicator_meta.get("id", indicator),
            "indicator_name_api": indicator_meta.get("value") or INDICATORS[indicator],
            "year": int(item["date"]) if item.get("date") else None,
            "value": item.get("value"),
            "unit": "indicator-defined; see World Bank indicator metadata",
            "source": "World Bank Indicators API",
            "source_url": resolved_url,
            "source_vintage": source_vintage,
            "retrieved_utc": retrieved,
        })
    return rows


def fetch_indicator_audited(
    codes: str | list[str], indicator: str, start: int, end: int,
    timeout: int = 60, session: requests.Session | None = None,
    snapshot_dir: Path | None = None,
) -> tuple[list[dict], dict]:
    """Fetch one indicator in country chunks and return rows plus a source audit record."""
    if indicator not in INDICATORS:
        raise KeyError(f"Unregistered macro-focus indicator: {indicator}")
    chunks = chunk_codes(codes)
    rows: list[dict] = []
    request_urls: list[str] = []
    raw_paths: list[str] = []
    errors: list[str] = []
    http_statuses: list[int] = []
    vintages: set[str] = set()
    owns_session = session is None
    http = session if session is not None else build_http_session()
    retrieved = datetime.now(timezone.utc).isoformat()
    snapshot_dir = snapshot_dir or (SNAPSHOT_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ"))
    try:
        for chunk_index, country_chunk in enumerate(chunks):
            url = f"{BASE_URL}/country/{';'.join(country_chunk)}/indicator/{indicator}"
            params = {"date": f"{start}:{end}", "format": "json", "per_page": 2000}
            request_urls.append(url)
            chunk_ok = False
            for attempt in range(CHUNK_ATTEMPTS):
                try:
                    response = get_with_dns_retries(
                        http, url, params=params, timeout=(15, timeout)
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
                        raise ValueError(f"Unexpected API response for {indicator}: {payload!r}")
                    metadata = payload[0]
                    source_vintage = str(metadata.get("lastupdated") or "not_exposed")
                    vintages.add(source_vintage)
                    retrieved = datetime.now(timezone.utc).isoformat()
                    raw_dir = snapshot_dir
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    raw_path = raw_dir / f"{indicator.replace('.', '_')}_chunk_{chunk_index:02d}.json"
                    raw_path.write_text(
                        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8"
                    )
                    raw_paths.append(str(raw_path.relative_to(ROOT)))
                    chunk_rows = _parse_payload(
                        payload, indicator, response.url, retrieved, source_vintage
                    )
                    rows.extend(chunk_rows)
                    http_statuses.append(int(response.status_code))
                    chunk_ok = True
                    break
                except (requests.RequestException, ValueError) as exc:
                    message = f"{url} (countries={';'.join(country_chunk)}): {type(exc).__name__}: {exc}"
                    if attempt + 1 < CHUNK_ATTEMPTS:
                        delay = min(2 ** attempt, 12) + random.uniform(0.0, 0.5)
                        print(
                            f"World Bank {indicator} chunk {chunk_index + 1}/{len(chunks)} "
                            f"failed (attempt {attempt + 1}/{CHUNK_ATTEMPTS}); retrying in {delay:.2f}s: {exc}"
                        )
                        time.sleep(delay)
                    else:
                        errors.append(message)
            if not chunk_ok:
                print(f"World Bank {indicator} chunk {chunk_index + 1}/{len(chunks)} remains failed.")
        fetched = len(rows)
        missing = sum(pd.isna(row.get("value")) for row in rows)
        status = "SUCCESS" if not errors else ("PARTIAL" if rows else "FAILED")
        audit = {
            "source_id": f"WDI_MACRO_FOCUS:{indicator}",
            "publisher": "World Bank",
            "source_type": "numeric_api",
            "dataset_id": indicator,
            "exact_url": request_urls[0] if request_urls else f"{BASE_URL}/country/{{country_codes}}/indicator/{indicator}",
            "request_urls_json": json.dumps(request_urls),
            "metadata_url": f"https://api.worldbank.org/v2/indicator/{indicator}",
            "retrieval_timestamp_utc": retrieved,
            "publication_release_date": "not exposed by the indicator response",
            "observation_period_start": start,
            "observation_period_end_requested": end,
            "observation_period_end_observed": max(
                (int(row["year"]) for row in rows if row.get("year") is not None and pd.notna(row.get("value"))),
                default=None
            ),
            "definition": INDICATORS[indicator],
            "unit": "indicator-defined; see World Bank metadata URL",
            "geography_scope": "registered global_country destinations in ISO3; country-year fallback, not bilateral",
            "origin_scope": "not applicable; national macro context",
            "destination_scope": "registered global_country destination countries",
            "cohort": "national aggregate; not migrant-specific",
            "revision_vintage": ";".join(sorted(vintages)) if vintages else "not_exposed",
            "fetch_status": status,
            "http_status": ";".join(str(v) for v in sorted(set(http_statuses))),
            "rows_fetched": fetched,
            "rows_normalized": fetched if status == "SUCCESS" else 0,
            "rows_inserted": 0,
            "rows_updated": 0,
            "rows_new_vintage_snapshots": 0,
            "rows_unchanged": 0,
            "rows_rejected": 0,
            "duplicate_rows": 0,
            "missing_values": missing,
            "missingness_pct": (100.0 * missing / fetched) if fetched else None,
            "raw_snapshot_paths_json": json.dumps(raw_paths),
            "normalized_output_path": str(OUT.relative_to(ROOT)),
            "counted_in_numeric_totals": status == "SUCCESS",
            "error": " | ".join(errors),
        }
        return rows, audit
    finally:
        if owns_session:
            http.close()


def fetch_indicator(
    codes: str, indicator: str, start: int, end: int,
    timeout: int = 60, session: requests.Session | None = None
) -> list[dict]:
    """Backward-compatible list-returning wrapper; all requests are chunked."""
    rows, audit = fetch_indicator_audited(codes, indicator, start, end, timeout, session)
    if audit["fetch_status"] != "SUCCESS":
        raise requests.exceptions.RequestException(
            f"World Bank {indicator} incomplete: {audit['error']}"
        )
    return rows


def append_macro_history(frame: pd.DataFrame, path: Path = HISTORY) -> dict:
    """Append new observations and versioned revisions; never overwrite prior vintages."""
    path.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(path, compression="gzip") if path.exists() else pd.DataFrame(columns=HISTORY_COLUMNS)
    if frame.empty:
        if not path.exists():
            old.to_csv(path, index=False, compression="gzip")
        return {"inserted": 0, "revised": 0, "new_vintage_snapshots": 0,
                "unchanged": 0, "stale": 0, "duplicates": 0, "history_rows": len(old)}
    key_cols = ["country_code", "indicator_code", "year"]
    current = frame.copy()
    current["record_hash"] = current.apply(
        lambda r: hashlib.sha256(
            "|".join(str(r.get(c, "")) for c in key_cols + ["source_vintage", "value"]).encode()
        ).hexdigest(), axis=1
    )
    duplicates = int(current.duplicated(key_cols, keep="last").sum())
    current = current.drop_duplicates(key_cols, keep="last")
    latest = {}
    if not old.empty:
        old = old.sort_values("retrieved_utc")
        for _, row in old.iterrows():
            latest[tuple(row[c] for c in key_cols)] = row
    append = []
    inserted = revised = new_vintage = unchanged = stale = 0
    by_indicator = {}
    for _, row in current.iterrows():
        key = tuple(row[c] for c in key_cols)
        indicator = str(row.get("indicator_code", ""))
        bucket = by_indicator.setdefault(indicator, {
            "inserted": 0, "revised": 0, "new_vintage_snapshots": 0,
            "unchanged": 0, "stale": 0
        })
        previous = latest.get(key)
        value = row.get("value")
        vintage = str(row.get("source_vintage") or "not_exposed")
        if previous is None:
            revision_number, revision_type, previous_value = 1, "initial", pd.NA
            inserted += 1
            bucket["inserted"] += 1
        else:
            old_value = previous.get("value")
            old_vintage = str(previous.get("source_vintage") or "not_exposed")
            if vintage != "not_exposed" and old_vintage != "not_exposed" and vintage < old_vintage:
                stale += 1
                bucket["stale"] += 1
                continue
            same_value = (pd.isna(value) and pd.isna(old_value)) or (
                pd.notna(value) and pd.notna(old_value) and float(value) == float(old_value)
            )
            if same_value and vintage == old_vintage:
                unchanged += 1
                bucket["unchanged"] += 1
                continue
            revision_number = int(previous.get("revision_number", 1)) + 1
            previous_value = old_value
            if same_value:
                revision_type = "source_vintage_snapshot_unchanged"
                new_vintage += 1
                bucket["new_vintage_snapshots"] += 1
            else:
                revision_type = "value_revision"
                revised += 1
                bucket["revised"] += 1
        record = row.to_dict()
        record.update({
            "revision_number": revision_number,
            "revision_type": revision_type,
            "previous_value": previous_value,
        })
        append.append(record)
        latest[key] = pd.Series(record)
    if append:
        old = pd.concat([old, pd.DataFrame(append)], ignore_index=True)
    for col in HISTORY_COLUMNS:
        if col not in old:
            old[col] = pd.NA
    old[HISTORY_COLUMNS].to_csv(path, index=False, compression="gzip")
    return {
        "inserted": inserted, "revised": revised,
        "new_vintage_snapshots": new_vintage, "unchanged": unchanged,
        "stale": stale, "duplicates": duplicates, "history_rows": len(old),
        "by_indicator": by_indicator
    }


def write_source_status(rows: list[dict]) -> None:
    STATUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(STATUS_OUT, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2010)
    parser.add_argument("--end", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must be <= --end")

    destinations = pd.read_csv(DESTINATIONS, dtype=str).fillna("")
    codes = sorted({
        c for c in destinations.loc[
            destinations["primary_choice_set"] == "global_country", "wb_country_code"
        ].tolist() if c
    })
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    snapshot_dir = SNAPSHOT_ROOT / run_id
    all_rows: list[dict] = []
    source_status: list[dict] = []
    with build_http_session() as session:
        for indicator in INDICATORS:
            print(f"Fetching {indicator} ({INDICATORS[indicator]}) in {len(chunk_codes(codes))} country batches...")
            rows, status = fetch_indicator_audited(
                codes, indicator, args.start, args.end,
                session=session, snapshot_dir=snapshot_dir
            )
            source_status.append(status)
            all_rows.extend(rows)

    write_source_status(source_status)
    failed = [r for r in source_status if r["fetch_status"] != "SUCCESS"]
    if failed:
        manifest = {
            "run_id": run_id,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PARTIAL_FAILED",
            "natural_key": ["country_code", "indicator_code", "year", "source_vintage"],
            "country_chunk_size": CHUNK_SIZE,
            "source_indicators": len(INDICATORS),
            "successful_indicators": len(source_status) - len(failed),
            "partial_or_failed_indicators": len(failed),
            "rows_fetched": int(sum(r["rows_fetched"] for r in source_status)),
            "normalized_panel_updated": False,
            "history_updated": False,
            "failed_indicators": [r["dataset_id"] for r in failed],
            "note": "Incomplete macro-focus retrieval: previous normalized panel and history were preserved; no partial ranking input was written."
        }
        MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(
            f"Macro-focus retrieval incomplete for {len(failed)} indicator(s); previous panel preserved. "
            f"See {STATUS_OUT.relative_to(ROOT)}."
        )

    frame = pd.DataFrame(all_rows)
    if frame.empty:
        raise RuntimeError("World Bank macro-focus API returned zero rows; previous panel preserved.")
    required = {"country_code", "indicator_code", "year", "value", "source_vintage"}
    if required - set(frame.columns):
        raise ValueError(f"Macro-focus panel missing required fields: {sorted(required - set(frame.columns))}")
    duplicates = int(frame.duplicated(["country_code", "indicator_code", "year"]).sum())
    if duplicates:
        raise ValueError(f"Macro-focus panel contains {duplicates} duplicate country-indicator-year keys.")
    history_stats = append_macro_history(frame)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)

    row_counts = frame.groupby("indicator_code", dropna=False).size().to_dict()
    history_by_indicator = history_stats.get("by_indicator", {})
    for row in source_status:
        indicator = row["dataset_id"]
        row["rows_normalized"] = int(row_counts.get(indicator, 0))
        stats = history_by_indicator.get(indicator, {})
        row["rows_inserted"] = int(stats.get("inserted", 0))
        row["rows_updated"] = int(stats.get("revised", 0))
        row["rows_new_vintage_snapshots"] = int(stats.get("new_vintage_snapshots", 0))
        row["rows_unchanged"] = int(stats.get("unchanged", 0))
        row["rows_rejected"] = int(stats.get("stale", 0))
        current = frame[frame["indicator_code"] == indicator]
        row["duplicate_rows"] = int(current.duplicated(["country_code", "year"]).sum())
        row["normalized_output_path"] = str(args.out.relative_to(ROOT))

    write_source_status(source_status)
    manifest = {
        "run_id": run_id,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS",
        "natural_key": ["country_code", "indicator_code", "year", "source_vintage"],
        "country_chunk_size": CHUNK_SIZE,
        "source_indicators": len(INDICATORS),
        "successful_indicators": len(source_status),
        "partial_or_failed_indicators": 0,
        "rows_fetched": int(sum(r["rows_fetched"] for r in source_status)),
        "rows_normalized": int(len(frame)),
        "history": history_stats,
        "normalized_panel_path": str(args.out.relative_to(ROOT)),
        "history_path": str(HISTORY.relative_to(ROOT)),
        "source_status_path": str(STATUS_OUT.relative_to(ROOT)),
        "raw_snapshot_root": str(snapshot_dir.relative_to(ROOT)),
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(frame):,} observations to {args.out}")
    print("Note: empty values are preserved as missing; no cross-country imputation was applied.")


if __name__ == "__main__":
    main()
