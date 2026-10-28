"""Supplemental official migration datasets used by the EOM research refresh.

The module downloads compact research extracts from the UNHCR open Data API,
UN DESA International Migrant Stock 2024 workbooks, and the OECD SDMX API.
Each extract is source-stamped; data are not merged into model scores here.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

UNHCR_EXPORT_URL = "https://api-data.unhcr.org/api/v0/data/export/PopStatsOfficial"
UNHCR_METADATA_URL = "https://api-data.unhcr.org/api/v0/metadata/PopStatsOfficial"
UNHCR_LABEL = "UNHCR Official population statistics on people affected by forced displacement and statelessness"

UNDESA_FILES = {
    "destination": (
        "undesa_pd_2024_ims_stock_by_sex_and_destination.xlsx",
        "https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_and_destination.xlsx",
    ),
    "origin": (
        "undesa_pd_2024_ims_stock_by_sex_and_origin.xlsx",
        "https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_and_origin.xlsx",
    ),
    "bilateral": (
        "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx",
        "https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx",
    ),
}
UNDESA_LANDING_URL = "https://www.un.org/development/desa/pd/content/international-migrant-stock"

# Query template copied from the OECD Data Explorer's official SDMX query
# for the International migration database. B11 and the remaining dimensions
# are retained in the output as source codes/labels; no semantic remapping of
# the measure is attempted by this adapter.
OECD_MIGRATION_QUERY = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0/.W.A.B11._T..."
)
OECD_MIGRATION_DATAFLOW_URL = (
    "https://sdmx.oecd.org/public/rest/dataflow/OECD.ELS.IMD/DSD_MIG@DF_MIG/1.0?references=all"
)

DESTINATION_CODES = {
    "GBR", "IRL", "NLD", "DEU", "CHE", "HKG", "JPN", "SGP", "AUS", "CAN",
    "USA", "NZL", "FRA", "ESP", "SWE", "DNK", "FIN", "NOR", "AUT", "CZE",
    "IND", "BRA",
}
ORIGIN_CODES = DESTINATION_CODES | {
    "CHN", "PHL", "PAK", "BGD", "NPL", "NGA", "UKR", "SYR", "AFG", "RUS",
    "VNM", "MEX", "IDN", "KOR", "TUR", "ZAF", "COL", "VEN", "ETH", "IRQ",
}
TOTAL_ORIGIN_CODES = {"", "_T", "T", "TOTAL", "ALL", "WORLD", "WLD", "999"}

UN_TO_ISO3_FOCUS = {
    "United Kingdom": "GBR", "United Kingdom of Great Britain and Northern Ireland": "GBR",
    "Ireland": "IRL", "Netherlands": "NLD", "The Netherlands": "NLD",
    "Germany": "DEU", "Switzerland": "CHE", "China, Hong Kong SAR": "HKG",
    "Hong Kong SAR": "HKG", "Japan": "JPN", "Singapore": "SGP",
    "Australia": "AUS", "Canada": "CAN", "United States of America": "USA",
    "United States": "USA", "New Zealand": "NZL", "France": "FRA",
    "Spain": "ESP", "Sweden": "SWE", "Denmark": "DNK", "Finland": "FIN",
    "Norway": "NOR", "Austria": "AUT", "Czechia": "CZE", "Czech Republic": "CZE",
    "India": "IND", "Brazil": "BRA",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _find_column(columns, candidates: tuple[str, ...]) -> str | None:
    mapping = {_norm(col): str(col) for col in columns}
    for candidate in candidates:
        if _norm(candidate) in mapping:
            return mapping[_norm(candidate)]
    return None


def _country_name_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _focus_name_to_iso3(root: Path) -> dict[str, str]:
    mapping = {_country_name_key(k): v for k, v in UN_TO_ISO3_FOCUS.items()}
    destinations = root / "data" / "destinations.csv"
    if destinations.exists():
        try:
            d = pd.read_csv(destinations)
            for _, row in d.iterrows():
                code = str(row.get("destination_id", "")).upper()
                name = str(row.get("destination_name", ""))
                if code in DESTINATION_CODES and name and name.lower() != "nan":
                    mapping[_country_name_key(name)] = code
        except Exception:
            pass
    world_bank = root / "data" / "raw" / "world_bank_long.csv"
    if world_bank.exists():
        try:
            wb = pd.read_csv(world_bank, usecols=["country_code", "country_name_api"])
            for _, row in wb.dropna().drop_duplicates().iterrows():
                mapping.setdefault(_country_name_key(row["country_name_api"]), str(row["country_code"]).upper())
        except Exception:
            pass
    return mapping


def fetch_unhcr_focus(session, root: Path, run_id: str) -> tuple[pd.DataFrame, dict]:
    """Stream the official UNHCR series and retain destination/origin-relevant rows.

    The source series is hundreds of thousands of records. The complete CSV is
    preserved as a run-specific raw snapshot and parsed in chunks. The compact
    focus extract keeps the original dimensions, source labels, footnotes and units.
    """
    row = {
        "source_id": "UNHCR_POPSTATS_OFFICIAL",
        "source": UNHCR_LABEL,
        "url": UNHCR_EXPORT_URL,
        "metadata_url": UNHCR_METADATA_URL,
        "checked_at_utc": _now(),
        "status": "FAILED",
        "source_rows": 0,
        "focus_rows": 0,
        "observation_start": "",
        "observation_end": "",
        "sha256_full_export": "",
        "error": "",
        "output_path": "data/raw/unhcr_forced_displacement_focus.csv.gz",
        "raw_snapshot_path": f"data/raw/snapshots/unhcr/{run_id}/PopStatsOfficial.csv",
    }
    digest = hashlib.sha256()
    kept: list[pd.DataFrame] = []
    total_rows = 0
    try:
        headers = {
            "User-Agent": "EOM-Research-ETL/2.2 (+reproducible academic research)",
            "Accept": "text/csv,*/*",
        }
        snapshot_dir = root / "data" / "raw" / "snapshots" / "unhcr" / run_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / "PopStatsOfficial.csv"
        partial_path = snapshot_dir / "PopStatsOfficial.csv.part"
        row["raw_snapshot_path"] = str(snapshot_path.relative_to(root))
        with partial_path.open("wb") as tmp:
            with session.get(UNHCR_EXPORT_URL, headers=headers, timeout=(15, 180), stream=True) as response:
                response.raise_for_status()
                content_type = str(response.headers.get("Content-Type", "")).lower()
                if "html" in content_type:
                    raise ValueError(f"UNHCR export unexpectedly returned HTML ({content_type})")
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if block:
                        digest.update(block)
                        tmp.write(block)
        partial_path.replace(snapshot_path)
        for chunk in pd.read_csv(snapshot_path, chunksize=50_000, low_memory=False):
            total_rows += len(chunk)
            period_col = _find_column(chunk.columns, ("time_period",))
            host_col = _find_column(chunk.columns, ("ref_area_adm0",))
            origin_col = _find_column(chunk.columns, ("area_ori_adm0",))
            value_col = _find_column(chunk.columns, ("obs_value",))
            if not all((period_col, host_col, origin_col, value_col)):
                raise ValueError(f"UNHCR export schema missing required columns; found {list(chunk.columns)[:30]}")
            host = chunk[host_col].fillna("").astype(str).str.upper().str.strip()
            origin = chunk[origin_col].fillna("").astype(str).str.upper().str.strip()
            host_focus = host.isin(DESTINATION_CODES)
            origin_focus = origin.isin(ORIGIN_CODES)
            # Keep every origin recorded for focus destinations, plus every
            # destination/asylum location recorded for selected focus origins.
            # Filtering origin categories at this point would drop valid flows
            # from other origins into a focus destination.
            mask = host_focus | origin_focus
            selected = chunk.loc[mask].copy()
            if selected.empty:
                continue
            selected["source"] = UNHCR_LABEL
            selected["source_url"] = UNHCR_EXPORT_URL
            selected["metadata_url"] = UNHCR_METADATA_URL
            selected["retrieved_utc"] = _now()
            selected["run_id"] = run_id
            selected["source_vintage"] = "UNHCR Data API export; latest available"
            kept.append(selected)
        result = pd.concat(kept, ignore_index=True, sort=False) if kept else pd.DataFrame()
        if result.empty:
            raise ValueError("UNHCR export succeeded but no records matched the focus-country filter")
        result_path = root / "data" / "raw" / "unhcr_forced_displacement_focus.csv.gz"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(result_path, index=False, compression="gzip")
        period_col = _find_column(result.columns, ("time_period",))
        periods = result[period_col].dropna().astype(str) if period_col else pd.Series(dtype=str)
        row.update({
            "status": "SUCCESS",
            "source_rows": total_rows,
            "focus_rows": len(result),
            "observation_start": periods.min() if not periods.empty else "",
            "observation_end": periods.max() if not periods.empty else "",
            "sha256_full_export": digest.hexdigest(),
        })
    except Exception as exc:
        partial_path = root / "data" / "raw" / "snapshots" / "unhcr" / run_id / "PopStatsOfficial.csv.part"
        if partial_path.exists():
            partial_path.unlink(missing_ok=True)
        row["error"] = f"{type(exc).__name__}: {exc}"
    return (result if "result" in locals() and not result.empty else pd.DataFrame()), row


def _parse_undesa_workbook(path: Path, direction: str, run_id: str, iso_map: dict[str, str]) -> pd.DataFrame:
    years = (1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024)
    sex_order = ("both", "male", "female")
    raw = pd.read_excel(path, sheet_name="Table 1", header=None, engine="openpyxl")
    output = []
    # The UN workbook places country name and UN M49 numeric code in columns 2 and 5.
    # Year blocks are arranged as both sexes, male, and female, eight points each.
    if raw.shape[1] < 29:
        raise ValueError(f"Unexpected UN DESA Table 1 layout: expected >=29 columns, got {raw.shape[1]}")
    for _, cells in raw.iterrows():
        country_name = cells.iloc[1] if len(cells) > 1 else None
        un_code = pd.to_numeric(pd.Series([cells.iloc[4]]), errors="coerce").iloc[0]
        if pd.isna(un_code) or not float(un_code).is_integer() or int(un_code) >= 900:
            continue
        if not isinstance(country_name, str) or not country_name.strip():
            continue
        name = country_name.strip()
        iso3 = iso_map.get(_country_name_key(name), "")
        for sex_idx, sex in enumerate(sex_order):
            for year_idx, year in enumerate(years):
                col = 5 + (sex_idx * len(years)) + year_idx
                value = pd.to_numeric(pd.Series([cells.iloc[col]]), errors="coerce").iloc[0]
                output.append({
                    "direction": direction,
                    "country_name": name,
                    "country_code_un": int(un_code),
                    "country_code_iso3": iso3,
                    "year": year,
                    "sex": {"both": "Total sexes", "male": "Male", "female": "Female"}[sex],
                    "migrant_stock_persons": None if pd.isna(value) else float(value),
                    "measure_type": "international_migrant_stock",
                    "stock_direction": "destination_stock" if direction == "destination" else "origin_stock_abroad",
                    "source": "UN DESA Population Division",
                    "source_dataset": "International Migrant Stock 2024",
                    "source_url": UNDESA_LANDING_URL,
                    "retrieved_utc": _now(),
                    "run_id": run_id,
                })
    df = pd.DataFrame(output)
    if df.empty:
        raise ValueError("No country rows parsed from UN DESA Table 1")
    return df



def _parse_undesa_bilateral_workbook(path: Path, run_id: str, iso_map: dict[str, str]) -> pd.DataFrame:
    """Parse the official bilateral origin-to-destination stock workbook.

    The official Table 1 layout is: index, destination name, coverage, data type,
    destination UN M49 code, origin name, origin UN M49 code, then 24 values
    grouped by sex (total, male, female) and year (1990--2024). The coverage
    and data-type columns are metadata, not geographic codes. Regional aggregates
    are not emitted as country pairs.
    """
    years = (1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024)
    sex_order = ("both", "male", "female")
    raw = pd.read_excel(path, sheet_name="Table 1", header=None, engine="openpyxl")
    if raw.shape[1] < 31:
        raise ValueError(f"Unexpected UN DESA bilateral layout: expected >=31 columns, got {raw.shape[1]}")
    output = []
    for _, cells in raw.iterrows():
        destination_name = cells.iloc[1] if len(cells) > 1 else None
        destination_code = pd.to_numeric(pd.Series([cells.iloc[4]]), errors="coerce").iloc[0] if len(cells) > 4 else float("nan")
        origin_name = cells.iloc[5] if len(cells) > 5 else None
        origin_code = pd.to_numeric(pd.Series([cells.iloc[6]]), errors="coerce").iloc[0] if len(cells) > 6 else float("nan")
        if (
            pd.isna(destination_code) or pd.isna(origin_code)
            or not float(destination_code).is_integer() or not float(origin_code).is_integer()
            or int(destination_code) >= 900 or int(origin_code) >= 900
        ):
            continue
        if not isinstance(destination_name, str) or not destination_name.strip():
            continue
        if not isinstance(origin_name, str) or not origin_name.strip():
            continue
        destination_name = destination_name.strip()
        origin_name = origin_name.strip()
        for sex_idx, sex in enumerate(sex_order):
            for year_idx, year in enumerate(years):
                col = 7 + (sex_idx * len(years)) + year_idx
                value = pd.to_numeric(pd.Series([cells.iloc[col]]), errors="coerce").iloc[0]
                output.append({
                    "direction": "bilateral",
                    "destination_name": destination_name,
                    "destination_code_un": int(destination_code),
                    "destination_code_iso3": iso_map.get(_country_name_key(destination_name), ""),
                    "origin_name": origin_name,
                    "origin_code_un": int(origin_code),
                    "origin_code_iso3": iso_map.get(_country_name_key(origin_name), ""),
                    "year": year,
                    "sex": {"both": "Total sexes", "male": "Male", "female": "Female"}[sex],
                    "migrant_stock_persons": None if pd.isna(value) else float(value),
                    "measure_type": "bilateral_international_migrant_stock",
                    "stock_direction": "origin_to_destination_stock",
                    "source": "UN DESA Population Division",
                    "source_dataset": "International Migrant Stock 2024",
                    "source_url": UNDESA_LANDING_URL,
                    "retrieved_utc": _now(),
                    "run_id": run_id,
                })
    df = pd.DataFrame(output)
    if df.empty:
        raise ValueError("No bilateral country-pair rows parsed from UN DESA Table 1")
    return df


def fetch_undesa_migrant_stock(session, root: Path, run_id: str) -> tuple[pd.DataFrame, list[dict]]:
    """Download official 2024 UN DESA migrant-stock destination and origin tables."""
    snapshot_dir = root / "data" / "raw" / "snapshots" / "undesa" / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    iso_map = _focus_name_to_iso3(root)
    outputs: list[pd.DataFrame] = []
    statuses: list[dict] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EOM-Research-ETL/2.2; +reproducible academic research)",
        "Referer": UNDESA_LANDING_URL,
    }
    for direction, (filename, url) in UNDESA_FILES.items():
        status = {
            "source_id": f"UN_DESA_IMS_2024_{direction.upper()}",
            "source": "UN DESA Population Division",
            "dataset": f"International Migrant Stock 2024 — {direction}",
            "url": url,
            "checked_at_utc": _now(),
            "status": "FAILED",
            "http_status": "",
            "rows_fetched": 0,
            "countries_fetched": 0,
            "sha256": "",
            "size_bytes": 0,
            "error": "",
            "output_path": "data/raw/undesa_migrant_stock_long.csv",
        }
        try:
            response = session.get(url, headers=headers, timeout=(15, 90))
            response.raise_for_status()
            body = response.content
            if not body.startswith(b"PK"):
                raise ValueError(f"Expected an XLSX workbook ZIP payload, received {response.headers.get('Content-Type')}")
            snapshot_path = snapshot_dir / filename
            snapshot_path.write_bytes(body)
            status["http_status"] = response.status_code
            status["sha256"] = hashlib.sha256(body).hexdigest()
            status["size_bytes"] = len(body)
            if direction == "bilateral":
                df = _parse_undesa_bilateral_workbook(snapshot_path, run_id, iso_map)
            else:
                df = _parse_undesa_workbook(snapshot_path, direction, run_id, iso_map)
            status["status"] = "SUCCESS"
            status["rows_fetched"] = len(df)
            if direction == "bilateral":
                status["countries_fetched"] = int(max(
                    df["destination_code_un"].nunique(),
                    df["origin_code_un"].nunique(),
                ))
                status["destination_countries_fetched"] = int(df["destination_code_un"].nunique())
                status["origin_countries_fetched"] = int(df["origin_code_un"].nunique())
            else:
                status["countries_fetched"] = int(df["country_code_un"].nunique())
            outputs.append(df)
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
        statuses.append(status)
    result = pd.concat(outputs, ignore_index=True, sort=False) if outputs else pd.DataFrame()
    if not result.empty:
        result_path = root / "data" / "raw" / "undesa_migrant_stock_long.csv"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        # If a temporary failure affects one workbook, retain that direction's
        # prior canonical data while replacing any successfully refreshed direction.
        successful_directions = {
            row.get("dataset", "").rsplit(" — ", 1)[-1]
            for row in statuses if row.get("status") == "SUCCESS"
        }
        old = pd.read_csv(result_path) if result_path.exists() else pd.DataFrame()
        if not old.empty and successful_directions:
            old = old[~old["direction"].astype(str).isin(successful_directions)]
        combined = pd.concat([old, result], ignore_index=True, sort=False)
        if not combined.empty:
            non_bilateral = combined[combined["direction"].astype(str) != "bilateral"]
            bilateral = combined[combined["direction"].astype(str) == "bilateral"]
            if not non_bilateral.empty:
                non_bilateral = non_bilateral.drop_duplicates(
                    ["direction", "country_code_un", "year", "sex"], keep="last"
                )
            if not bilateral.empty:
                bilateral = bilateral.drop_duplicates(
                    ["direction", "destination_code_un", "origin_code_un", "year", "sex"], keep="last"
                )
            combined = pd.concat([non_bilateral, bilateral], ignore_index=True, sort=False)
        combined.to_csv(result_path, index=False)
    return result, statuses


def fetch_oecd_migration_slice(session, root: Path, run_id: str, start_year: int, end_year: int) -> tuple[pd.DataFrame, dict]:
    """Fetch a bounded, official OECD migration-database slice for focus geographies."""
    params = {
        "startPeriod": str(start_year),
        "endPeriod": str(end_year),
        "dimensionAtObservation": "AllDimensions",
        "format": "csvfilewithlabels",
    }
    request_url = requests.Request("GET", OECD_MIGRATION_QUERY, params=params).prepare().url
    status = {
        "source_id": "OECD_DF_MIG_B11",
        "source": "OECD International migration database (SDMX)",
        "dataset": "DSD_MIG@DF_MIG; official Explorer query selector .W.A.B11._T...",
        "url": request_url,
        "request_url": request_url,
        "url_base": OECD_MIGRATION_QUERY,
        "request_params": json.dumps(params, sort_keys=True),
        "metadata_url": OECD_MIGRATION_DATAFLOW_URL,
        "checked_at_utc": _now(),
        "status": "FAILED",
        "rows_fetched": 0,
        "rows_focus": 0,
        "observation_start": start_year,
        "observation_end_requested": end_year,
        "error": "",
        "output_path": "data/raw/oecd_migration_database_focus.csv",
        "raw_snapshot_path": f"data/raw/snapshots/oecd/{run_id}/international_migration_database.csv",
    }
    try:
        response = session.get(OECD_MIGRATION_QUERY, params=params, timeout=(15, 120))
        response.raise_for_status()
        snapshot_path = root / "data" / "raw" / "snapshots" / "oecd" / run_id / "international_migration_database.csv"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(response.content)
        text = response.text
        if not text.strip() or text.lstrip().lower().startswith(("<!doctype html", "<html")):
            raise ValueError("OECD API returned empty or HTML content instead of a CSV series")
        from io import StringIO
        df = pd.read_csv(StringIO(text), low_memory=False)
        df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
        time_col = _find_column(df.columns, ("TIME_PERIOD",))
        value_col = _find_column(df.columns, ("OBS_VALUE",))
        if not time_col or not value_col:
            raise ValueError(f"OECD CSV schema lacked TIME_PERIOD/OBS_VALUE; columns={list(df.columns)[:25]}")
        geography_col = _find_column(df.columns, ("REF_AREA",))
        if not geography_col:
            raise ValueError(f"OECD CSV schema lacked REF_AREA geography code; columns={list(df.columns)[:25]}")
        geo = df[geography_col].fillna("").astype(str).str.upper().str.strip()
        focus = df.loc[geo.isin(DESTINATION_CODES | ORIGIN_CODES)].copy()
        if focus.empty:
            raise ValueError("OECD query returned data but no focus geographies were found in REF_AREA")
        focus["source"] = "OECD International migration database"
        focus["source_url"] = response.url if "?" in str(response.url) else request_url
        focus["metadata_url"] = OECD_MIGRATION_DATAFLOW_URL
        focus["retrieved_utc"] = _now()
        focus["run_id"] = run_id
        focus["dataset_selector"] = ".W.A.B11._T..."
        focus["measure_interpretation_status"] = "raw_source_measure_code; inspect dimension labels before modelling"
        out = root / "data" / "raw" / "oecd_migration_database_focus.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        focus.to_csv(out, index=False)
        status.update({
            "status": "SUCCESS",
            "url": response.url if "?" in str(response.url) else request_url,
            "response_url": response.url,
            "rows_fetched": len(df),
            "rows_focus": len(focus),
            "observation_start": str(focus[time_col].min()),
            "sha256_response": hashlib.sha256(response.content).hexdigest(),
        })
        return focus, status
    except Exception as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
        return pd.DataFrame(), status


ILOSTAT_API_URL = "https://rplumber.ilo.org/data/indicator"
ILOSTAT_TOC_URL = "https://rplumber.ilo.org/metadata/toc/indicator"
ILOSTAT_MIGRATION_INDICATORS = {
    "POP_XFRB_SEX_CBR_NB": "Working-age foreign-born population by sex and country of birth (thousands)",
    "EMP_XFRB_SEX_CBR_NB": "Employed foreign-born population by sex and country of birth (thousands)",
    "POP_XFLB_SEX_CBR_NB": "Inflow of working-age foreign-born population by sex and country of birth (thousands)",
}


def fetch_ilostat_annual_dataset_ids(session, snapshot_dir: Path | None = None) -> dict[str, str]:
    """Resolve current annual dataset IDs by official ILOSTAT catalogue labels.

    Legacy IDs are intentionally not trusted: ILOSTAT has deprecated some older
    identifiers. Resolve each requested series from the provider's live TOC instead.
    """
    from io import StringIO

    response = session.get(
        ILOSTAT_TOC_URL,
        params={"lang": "en", "format": ".csv"},
        timeout=(15, 60),
    )
    response.raise_for_status()
    body = response.text
    if snapshot_dir is not None:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "indicator_catalogue.csv").write_bytes(response.content)
    if not body.strip() or body.lstrip().startswith("<"):
        raise ValueError("ILOSTAT indicator catalogue returned empty or non-CSV content")
    catalog = pd.read_csv(StringIO(body), low_memory=False)
    catalog.columns = [str(col).replace("\ufeff", "").strip() for col in catalog.columns]
    id_col = _find_column(catalog.columns, ("id",))
    label_col = _find_column(catalog.columns, ("indicator.label", "indicator_label", "label"))
    freq_col = _find_column(catalog.columns, ("freq",))
    freq_label_col = _find_column(catalog.columns, ("freq.label", "freq_label"))
    if not id_col or not label_col:
        raise ValueError(
            "ILOSTAT catalogue missing id/indicator label columns; "
            f"columns={list(catalog.columns)[:30]}"
        )

    resolved: dict[str, str] = {}
    for legacy_id, expected_label in ILOSTAT_MIGRATION_INDICATORS.items():
        expected_key = _norm(expected_label)
        label_values = catalog[label_col].fillna("").astype(str).map(_norm)
        matches = catalog.loc[label_values == expected_key].copy()
        if matches.empty:
            # Allow harmless wording additions around the expected label, but do
            # not choose unrelated indicators based on a broad keyword search.
            matches = catalog.loc[label_values.map(
                lambda value: value.startswith(expected_key) or expected_key.startswith(value)
                if value else False
            )].copy()

        if matches.empty:
            continue

        annual_mask = pd.Series(False, index=matches.index)
        if freq_col:
            annual_mask |= matches[freq_col].fillna("").astype(str).map(_norm).isin({"a", "annual", "annually"})
        if freq_label_col:
            annual_mask |= matches[freq_label_col].fillna("").astype(str).map(_norm).isin({"a", "annual", "annually"})
        id_values = matches[id_col].fillna("").astype(str)
        annual_mask |= id_values.str.upper().str.endswith("_A")
        annual = matches.loc[annual_mask].copy()
        if annual.empty:
            continue
        # Prefer an explicit annual-frequency row and a stable ID when duplicate
        # catalogue aliases exist. Refuse ambiguity rather than guessing silently.
        annual_ids = sorted(set(annual[id_col].dropna().astype(str).str.strip()) - {""})
        if len(annual_ids) == 1:
            resolved[legacy_id] = annual_ids[0]
        elif annual_ids:
            with_suffix = [value for value in annual_ids if value.upper().endswith("_A")]
            if len(with_suffix) == 1:
                resolved[legacy_id] = with_suffix[0]
    return resolved

def filter_ilostat_focus(df: pd.DataFrame) -> pd.DataFrame:
    """Keep destination-country rows for the registered country comparison set.

    All classif1/classif2 origin, sex, source, note and status dimensions remain
    intact, so country-of-birth breakdowns are not collapsed into totals.
    """
    if df.empty:
        return df.copy()
    columns = {_norm(c): str(c) for c in df.columns}
    area_col = columns.get("refarea")
    if not area_col:
        raise ValueError(f"ILOSTAT response has no ref_area column; columns={list(df.columns)[:30]}")
    area = df[area_col].fillna("").astype(str).str.upper().str.strip()
    return df.loc[area.isin(DESTINATION_CODES)].copy()


def fetch_ilostat_migration_focus(
    session,
    root: Path,
    run_id: str,
    start_year: int,
    end_year: int,
) -> tuple[pd.DataFrame, list[dict]]:
    """Fetch selected official ILOSTAT international-labour-migration series.

    Each indicator is fetched independently. Successful indicators refresh only
    their own slice of the canonical extract; failed indicators preserve prior
    canonical rows. All ILO source labels/notes/dimensions remain unmodified.
    """
    out_path = root / "data" / "raw" / "ilostat_migrant_labour_focus.csv"
    old = pd.read_csv(out_path, low_memory=False) if out_path.exists() else pd.DataFrame()
    new_frames: list[pd.DataFrame] = []
    statuses: list[dict] = []
    successful_ids: set[str] = set()
    snapshot_dir = root / "data" / "raw" / "snapshots" / "ilostat" / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    try:
        current_dataset_ids = fetch_ilostat_annual_dataset_ids(session, snapshot_dir=snapshot_dir)
        catalogue_error = ""
    except Exception as exc:
        current_dataset_ids = {}
        catalogue_error = f"{type(exc).__name__}: {exc}"

    for legacy_id, label in ILOSTAT_MIGRATION_INDICATORS.items():
        query_end_year = min(int(end_year), datetime.now(timezone.utc).year - 1)
        dataset_id = current_dataset_ids.get(legacy_id, "")
        status = {
            "source_id": f"ILOSTAT_{legacy_id}",
            "source": "International Labour Organization (ILOSTAT)",
            "indicator_code": dataset_id,
            "legacy_indicator_code": legacy_id,
            "indicator_label_expected": label,
            "url": ILOSTAT_API_URL,
            "catalogue_url": ILOSTAT_TOC_URL,
            "checked_at_utc": _now(),
            "status": "FAILED",
            "rows_fetched": 0,
            "rows_focus": 0,
            "geographies": 0,
            "observation_start": start_year,
            "observation_end_requested": end_year,
            "observation_end_queried": query_end_year,
            "request_variant": "",
            "sha256_response": "",
            "error": "",
            "output_path": "data/raw/ilostat_migrant_labour_focus.csv",
            "catalogue_snapshot_path": f"data/raw/snapshots/ilostat/{run_id}/indicator_catalogue.csv",
            "raw_snapshot_path": "",
        }

        if not dataset_id:
            if catalogue_error:
                # A catalogue outage should not make the whole data refresh abort.
                # Try the modern annual suffix as a fallback, while preserving the
                # catalogue error in status for auditability.
                dataset_id = f"{legacy_id}_A"
                status["indicator_code"] = dataset_id
                status["id_resolution"] = "annual_suffix_fallback_after_catalogue_error"
                status["catalogue_error"] = catalogue_error
            else:
                status["error"] = (
                    f"No unique annual ILOSTAT dataset ID found for label {label!r} "
                    f"in the official indicator catalogue"
                )
                statuses.append(status)
                continue
        else:
            status["id_resolution"] = "official_catalogue_label_match"

        # Use ILOSTAT's documented R Plumber data endpoint with CSV output.
        # The .rds parser caused a native process crash (exit 139) in the live
        # refresh; CSV avoids that native parser and supports bounded year queries.
        from io import BytesIO

        snapshot_path = snapshot_dir / f"{dataset_id}.csv"
        status["raw_snapshot_path"] = str(snapshot_path.relative_to(root))
        data_url = "https://rplumber.ilo.org/data/indicator"
        params = {
            "id": dataset_id,
            "lang": "en",
            "type": "both",
            "format": ".csv",
            "timefrom": int(start_year),
            "timeto": int(query_end_year),
        }
        request_url = requests.Request("GET", data_url, params=params).prepare().url
        status["url"] = request_url
        status["request_url"] = request_url
        status["url_base"] = data_url
        status["request_params"] = json.dumps(params, sort_keys=True)
        parsed_raw = None
        selected_variant = "rplumber_csv_year_bounded"
        response = None
        failures = []
        try:
            response = session.get(data_url, params=params, timeout=(15, 120))
            response.raise_for_status()
            snapshot_path.write_bytes(response.content)
            if not response.content:
                raise ValueError("ILOSTAT data endpoint returned an empty response")
            candidate = pd.read_csv(BytesIO(response.content), low_memory=False)
            candidate.columns = [str(col).replace("\\ufeff", "").strip() for col in candidate.columns]
            norm_columns = {_norm(col): str(col) for col in candidate.columns}
            time_col = norm_columns.get("time")
            value_col = norm_columns.get("obsvalue")
            indicator_col = norm_columns.get("indicator")
            area_col = norm_columns.get("refarea")
            if not all((time_col, value_col, indicator_col, area_col)):
                raise ValueError(
                    f"ILOSTAT CSV schema missing required columns; columns={list(candidate.columns)[:30]}"
                )
            candidate[time_col] = pd.to_numeric(candidate[time_col], errors="coerce")
            candidate = candidate[candidate[time_col].between(start_year, query_end_year, inclusive="both")].copy()
            if candidate.empty:
                raise ValueError(f"ILOSTAT dataset had no rows between {start_year} and {query_end_year}")
            parsed_raw = candidate
        except Exception as exc:
            failures.append(f"rplumber_csv_year_bounded: {type(exc).__name__}: {exc}")

        if parsed_raw is None:
            status["error"] = "All ILOSTAT request variants failed: " + " | ".join(failures)
            statuses.append(status)
            continue

        try:
            time_col = _find_column(parsed_raw.columns, ("time",))
            area_col = _find_column(parsed_raw.columns, ("ref_area",))
            filtered = filter_ilostat_focus(parsed_raw)
            if filtered.empty:
                raise ValueError(
                    f"ILOSTAT returned {len(parsed_raw)} rows for {dataset_id} but none matched "
                    "registered destination codes"
                )

            filtered["retrieved_utc"] = _now()
            filtered["run_id"] = run_id
            filtered["source_url"] = response.url if "?" in str(response.url) else request_url
            filtered["source_dataset"] = dataset_id
            filtered["source_publisher"] = "International Labour Organization (ILOSTAT)"
            new_frames.append(filtered)
            successful_ids.add(dataset_id)
            time_values = pd.to_numeric(filtered[time_col], errors="coerce").dropna()
            status.update({
                "status": "SUCCESS",
                "url": response.url if "?" in str(response.url) else request_url,
                "response_url": response.url,
                "rows_fetched": len(parsed_raw),
                "rows_focus": len(filtered),
                "geographies": int(filtered[area_col].nunique()),
                "observation_start": int(time_values.min()) if not time_values.empty else "",
                "observation_end": int(time_values.max()) if not time_values.empty else "",
                "request_variant": selected_variant,
                "sha256_response": hashlib.sha256(response.content).hexdigest(),
                "error": "" if not failures else "Recovered after fallback: " + " | ".join(failures),
            })
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
        statuses.append(status)

    fresh = pd.concat(new_frames, ignore_index=True, sort=False) if new_frames else pd.DataFrame()
    if not fresh.empty:
        combined = pd.concat([old, fresh], ignore_index=True, sort=False)
        # Merge at observation-key level rather than replacing whole indicators:
        # a requested time window must not erase older or newer stored years, and
        # source rows omitted from a new vintage must not silently delete prior data.
        dimension_keys = [
            key for key in (
                "indicator", "ref_area", "sex", "classif1", "classif2",
                "time", "source",
            ) if key in combined.columns
        ]
        if dimension_keys:
            combined = combined.drop_duplicates(dimension_keys, keep="last")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(out_path, index=False)
    return fresh, statuses
