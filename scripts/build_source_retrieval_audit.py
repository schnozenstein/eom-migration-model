#!/usr/bin/env python3
"""Build a consolidated, source-level retrieval and data-quality audit."""
from __future__ import annotations
import csv, hashlib, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/"metadata"
OUT=ROOT/"outputs"
FIELDS=[
"workflow_run_id","etl_run_id","etl_outcome","source_id","publisher","source_type","dataset_id",
"exact_url","request_urls_json","metadata_url","retrieval_timestamp_utc","publication_release_date",
"observation_period_start","observation_period_end_requested","observation_period_end_observed",
"definition","unit","geography_scope","origin_scope","destination_scope","cohort","revision_vintage",
"fetch_status","http_status","rows_fetched","rows_normalized","rows_inserted","rows_updated",
"rows_rejected","duplicate_rows","missing_values","missingness_pct","unchanged_rows_skipped",
"sha256","raw_snapshot_path","normalized_output_path","counted_in_numeric_totals",
"validation_status","error","notes"]
LINEAGE_FIELDS=[
"workflow_run_id","etl_run_id","source_id","publisher","source_type","dataset_id","exact_url","metadata_url",
"retrieval_timestamp_utc","publication_release_date","observation_period_start","observation_period_end_observed",
"definition","unit","geography_scope","origin_scope","destination_scope","cohort","revision_vintage","fetch_status",
"http_status","sha256","raw_snapshot_path","normalized_output_path","notes"]

WDI_UNITS={
"BX.KLT.DINV.WD.GD.ZS":"% of GDP",
"BX.TRF.PWKR.CD.DT":"current US dollars",
"FP.CPI.TOTL.ZG":"annual percent change",
"GC.DOD.TOTL.GD.ZS":"% of GDP",
"GE.EST":"governance index estimate",
"IT.NET.USER.ZS":"% of population",
"NE.TRD.GNFS.ZS":"% of GDP",
"NY.GDP.MKTP.KD.ZG":"annual percent change",
"NY.GDP.MKTP.PP.CD":"current international dollars",
"NY.GDP.PCAP.CD":"current US dollars per person",
"NY.GDP.PCAP.PP.KD":"constant 2021 international dollars per person",
"NY.GDP.TOTL.RT.ZS":"% of GDP",
"PA.NUS.PPP":"local currency units per international dollar",
"PA.NUS.PRVT.PP":"local currency units per international dollar",
"PV.EST":"governance index estimate",
"RQ.EST":"governance index estimate",
"SE.SEC.ENRR":"% gross enrollment",
"SE.TER.ENRR":"% gross enrollment",
"SE.XPD.TOTL.GD.ZS":"% of GDP",
"SH.XPD.CHEX.GD.ZS":"% of GDP",
"SI.POV.GINI":"Gini index; source-defined scale",
"SL.EMP.TOTL.SP.ZS":"% of population age 15+",
"SL.TLF.CACT.FE.ZS":"% of female population ages 15+",
"SL.TLF.CACT.MA.ZS":"% of male population ages 15+",
"SL.TLF.CACT.ZS":"% of population",
"SL.UEM.1524.ZS":"% of labour force ages 15–24",
"SL.UEM.TOTL.ZS":"% of labour force",
"SM.POP.NETM":"persons; national net migration estimate",
"SP.DYN.CBRT.IN":"births per 1,000 population",
"SP.DYN.CDRT.IN":"deaths per 1,000 population",
"SP.DYN.IMRT.IN":"deaths per 1,000 live births",
"SP.DYN.LE00.FE.IN":"years",
"SP.DYN.LE00.IN":"years",
"SP.DYN.LE00.MA.IN":"years",
"SP.DYN.TFRT.IN":"births per woman",
"SP.POP.1564.TO.ZS":"% of population",
"SP.POP.GROW":"annual percent change",
"SP.POP.TOTL":"persons",
"SP.URB.TOTL.IN.ZS":"% of population"}

def read_csv(path:Path)->pd.DataFrame:
    if not path.exists() or path.stat().st_size==0: return pd.DataFrame()
    try: return pd.read_csv(path,dtype=str,keep_default_na=False,low_memory=False)
    except Exception: return pd.DataFrame()
def read_json(path:Path,default=None):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {} if default is None else default
def first(row:dict,*keys,default=""):
    for k in keys:
        v=row.get(k,"")
        if v is not None and str(v).strip() not in ("","nan","None"): return str(v).strip()
    return default
def as_int(v,default=0):
    try: return int(float(str(v)))
    except Exception: return default
def parse_urls(v,fallback=""):
    if isinstance(v,list): return [str(x) for x in v if str(x)]
    try:
        x=json.loads(str(v))
        if isinstance(x,list): return [str(y) for y in x if str(y)]
    except Exception: pass
    return [str(v)] if str(v).strip() else ([fallback] if fallback else [])
def sha256_file(path):
    if not path or not Path(path).exists() or not Path(path).is_file(): return ""
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def rel(path):
    try: return str(Path(path).resolve().relative_to(ROOT.resolve()))
    except Exception: return str(path or "")
def norm_http(value):
    try: return str(int(float(str(value).strip())))
    except Exception: return str(value or "").strip()
def success(status,http=""):
    h=norm_http(http)
    return str(status).upper() in {"SUCCESS","OK","PASS","200"} and (not h or h=="200")
def blank_row(run_id,etl_run_id,etl_outcome,**kwargs):
    r={k:"" for k in FIELDS}
    r.update({"workflow_run_id":run_id,"etl_run_id":etl_run_id,"etl_outcome":etl_outcome,
    "counted_in_numeric_totals":"false","validation_status":"NOT_ASSESSED"})
    r.update({k:("" if v is None else v) for k,v in kwargs.items() if k in r})
    if r.get("http_status"):
        r["http_status"]=norm_http(r["http_status"])
    return r
def snapshot_for(source,tokens=None,explicit=""):
    if explicit:
        p=Path(explicit); p=p if p.is_absolute() else ROOT/p
        if p.exists():
            if p.is_file(): return p
            files=sorted((x for x in p.rglob("*") if x.is_file()),key=lambda x:x.stat().st_mtime)
            matched=[x for x in files if tokens and all(t.lower() in x.name.lower() for t in tokens)]
            if matched: return matched[-1]
            if files: return files[-1]
    base=ROOT/"data"/"raw"/"snapshots"/source
    if not base.exists(): return None
    files=sorted((x for x in base.rglob("*") if x.is_file()),key=lambda x:x.stat().st_mtime)
    matched=[x for x in files if tokens and all(t.lower() in x.name.lower() for t in tokens)]
    return matched[-1] if matched else (files[-1] if files else None)
def release_from_snapshot(path):
    if not path or Path(path).suffix.lower()!=".json": return ""
    try:
        x=json.loads(Path(path).read_text(encoding="utf-8"))
        return str(x[0].get("lastupdated","")) if isinstance(x,list) and x and isinstance(x[0],dict) else ""
    except Exception: return ""
def numeric_stats(df,candidates):
    if df.empty: return 0,0,0.0
    col=next((c for c in candidates if c in df.columns),"")
    if not col: return len(df),0,0.0
    vals=pd.to_numeric(df[col],errors="coerce"); missing=int(vals.isna().sum())
    return len(df),missing,round(missing/len(df)*100,4) if len(df) else 0.0
def natural_duplicates(df,source):
    if df.empty: return 0
    candidates={
    "WDI":["country_code","indicator_code","year"],
    "Eurostat":["geo_code","year","indicator","source_dataset"],
    "OECD":["REF_AREA","MEASURE","FREQ","TIME_PERIOD","UNIT_MEASURE","UNIT_MULT","SEX","BIRTH_PLACE","CITIZENSHIP","EDUCATION_LEV"],
    "ILOSTAT":["ref_area","indicator","sex","classif1","time"],
    "UNHCR":["time_period","time_period_format","pop_type","pop_type_O","ref_area_region_unhcr","ref_area_adm0","ref_area_adm1","ref_area_adm2","ref_area_place","area_ori_region_unhcr","area_ori_adm0","area_ori_adm1","area_ori_adm2","area_ori_place","area_ori_O","sex","age","urbanisation","setting","nationality","disability","other_disag","other_disag_O","unit_measure","unit_mult","unit_comp","nature","reporting_type","deviations","compiling_org","data_series","data_source","date_coverage_start","date_coverage_end"],
    "UN DESA":["direction","country_code_un","origin_code_un","destination_code_un","year","sex"],
    "Brazil WDI":["country_code","indicator_code","year"],
    "PolicyPage":["url"],"OBMigra":["url"]}
    keys=[c for c in candidates.get(source,[]) if c in df.columns]
    return int(df.duplicated(subset=keys).sum()) if keys else int(df.duplicated().sum())

def main():
    OUT.mkdir(parents=True,exist_ok=True); META.mkdir(parents=True,exist_ok=True)
    workflow_id=str(os.environ.get("GITHUB_RUN_ID",""))
    etl_outcome=str(os.environ.get("EOM_ETL_OUTCOME","unknown")).lower()
    manifests=sorted((META/"refresh_runs").glob("*.json"))
    refresh=read_json(manifests[-1]) if manifests else {}
    etl_run_id=str(refresh.get("run_id",""))
    manifest_current=bool(workflow_id and str(refresh.get("github_workflow_run_id",""))==workflow_id)
    panel_path=ROOT/"data"/"raw"/"world_bank_long.csv"
    panel=read_csv(panel_path)
    if not panel.empty:
        panel["year_num"]=pd.to_numeric(panel.get("year",pd.Series(dtype=str)),errors="coerce")
        panel["value_num"]=pd.to_numeric(panel.get("value",pd.Series(dtype=str)),errors="coerce")
    rows=[]
    wdi_status=read_csv(META/"live_source_status.csv")
    for st in wdi_status.to_dict("records") if not wdi_status.empty else []:
        code=first(st,"indicator","indicator_code")
        g=panel[panel.get("indicator_code",pd.Series(dtype=str)).astype(str).eq(code)] if not panel.empty and code else pd.DataFrame()
        urls=parse_urls(st.get("request_urls",""),first(st,"url")); url=urls[0] if urls else first(st,"url")
        api_code=first(st,"api_indicator_code","indicator_api_code")
        if not api_code:
            m=re.search(r"/indicator/([^?]+)",url); api_code=m.group(1) if m else code
        snap=snapshot_for("world_bank",[api_code.replace(".","_"),"page"],first(st,"snapshot_dir")) if api_code else snapshot_for("world_bank",None,first(st,"snapshot_dir"))
        n=len(g); missing=int(g["value_num"].isna().sum()) if n and "value_num" in g.columns else ""
        miss=round(missing/n*100,4) if n and isinstance(missing,int) else ""
        dup=natural_duplicates(g,"WDI") if n else 0
        years=pd.to_numeric(g.loc[g["value_num"].notna(),"year"],errors="coerce") if n and "value_num" in g.columns else pd.Series(dtype=float)
        release=release_from_snapshot(snap) or first(st,"api_lastupdated")
        status=first(st,"status",default="UNKNOWN")
        rows.append(blank_row(workflow_id,etl_run_id,etl_outcome,
            source_id=f"WDI:{code}",publisher="World Bank",source_type="numeric_api",dataset_id=code,
            exact_url=url,request_urls_json=json.dumps(urls,ensure_ascii=False),
            metadata_url="https://api.worldbank.org/v2/indicator/"+code,
            retrieval_timestamp_utc=first(st,"checked_at_utc","retrieved_utc","retrieved_at_utc","retrieval_timestamp_utc",default=etl_run_id),
            publication_release_date=release or "not exposed by endpoint",
            observation_period_start=str(int(years.min())) if len(years.dropna()) else "",
            observation_period_end_requested=first(st,"observation_end_requested",default="2026"),
            observation_period_end_observed=str(int(years.max())) if len(years.dropna()) else "",
            definition=first(g.iloc[0].to_dict(),"indicator_name_api") if n else code,
            unit=WDI_UNITS.get(code,"indicator-specific; consult official World Bank indicator metadata"),
            geography_scope=f"{g['country_code'].nunique() if n and 'country_code' in g.columns else 0} country/aggregate entities; country-year panel",
            origin_scope="not available; not bilateral",destination_scope="not available; not bilateral",
            cohort="national total; indicator-specific denominator",revision_vintage=release,
            fetch_status=status,http_status=first(st,"http_status",default="200" if success(status) else ""),
            rows_fetched=as_int(first(st,"rows_fetched"),n),rows_normalized=n,
            rows_inserted=as_int(refresh.get("world_bank_history_new_keys",0)),
            rows_updated=as_int(refresh.get("world_bank_history_value_revisions",0)),
            rows_rejected=as_int(refresh.get("world_bank_rows_rejected",0)),
            duplicate_rows=dup,missing_values=missing,missingness_pct=miss,
            unchanged_rows_skipped=n if as_int(refresh.get("world_bank_history_new_keys",0))==0 and as_int(refresh.get("world_bank_history_value_revisions",0))==0 else "",
            sha256=sha256_file(snap) if snap else "",raw_snapshot_path=rel(snap) if snap else first(st,"snapshot_dir"),
            normalized_output_path=rel(panel_path),counted_in_numeric_totals="true",
            validation_status="PASS" if dup==0 else "FAIL",error=first(st,"error"),
            notes="Country-year fallback, not bilateral flow. Insert/revision counts are global WDI history totals, not allocated per indicator."
        ))
    euro=read_csv(META/"eurostat_source_status.csv"); euro_data=read_csv(ROOT/"data"/"raw"/"eurostat_migration_flows.csv")
    for st in euro.to_dict("records") if not euro.empty else []:
        dataset=first(st,"dataset","source_dataset","indicator")
        g=euro_data[euro_data.get("source_dataset",pd.Series(dtype=str)).astype(str).eq(dataset)] if not euro_data.empty and dataset else euro_data
        n,missing,miss=numeric_stats(g,["value"]); dup=natural_duplicates(g,"Eurostat")
        status=first(st,"status",default="UNKNOWN"); snap=snapshot_for("eurostat",[dataset])
        rows.append(blank_row(workflow_id,etl_run_id,etl_outcome,
            source_id=f"Eurostat:{dataset}",publisher="Eurostat",source_type="numeric_api",dataset_id=dataset,
            exact_url=first(st,"url"),request_urls_json=json.dumps([first(st,"url")]),
            retrieval_timestamp_utc=first(st,"checked_at_utc","retrieved_utc","retrieved_at_utc","retrieval_timestamp_utc",default=etl_run_id),
            publication_release_date=first(st,"release_date",default="not exposed by dataset API"),
            observation_period_start=first(st,"observation_start"),observation_period_end_requested=first(st,"observation_end_requested"),
            observation_period_end_observed=first(st,"observation_end"),
            definition="Annual immigration/emigration totals under selected total-age/sex dimensions; not bilateral origin-destination flows.",
            unit=first(st,"unit",default="number of persons"),geography_scope=first(st,"geographies_fetched",default="reporting geographies"),
            origin_scope="not preserved in current compact output",destination_scope="reporting geography",
            cohort="selected total age/sex dimensions",revision_vintage=sha256_file(snap) if snap else "",
            fetch_status=status,http_status=first(st,"http_status",default="200" if success(status) else ""),
            rows_fetched=as_int(first(st,"rows_fetched"),n),rows_normalized=n,rows_rejected="",
            duplicate_rows=dup,missing_values=missing,missingness_pct=miss,sha256=sha256_file(snap) if snap else "",
            raw_snapshot_path=rel(snap) if snap else "",normalized_output_path=rel(ROOT/"data"/"raw"/"eurostat_migration_flows.csv"),
            counted_in_numeric_totals="true",validation_status="PASS" if dup==0 else "WARN",error=first(st,"error"),
            notes="Normalized extract refreshed as a snapshot; per-row revision ledger not yet implemented."
        ))
    configs=[
    ("OECD","oecd_source_status.csv","oecd","data/raw/oecd_migration_database_focus.csv","numeric_download","OECD International Migration Database; B11 measure selector preserved but not yet interpreted.","source-defined; inspect UNIT_MEASURE/UNIT_MULT"),
    ("ILOSTAT","ilostat_source_status.csv","ilostat","data/raw/ilostat_migrant_labour_focus.csv","numeric_api","Official labour migration indicators; dimensions/classifications retained.","indicator-specific; use source label"),
    ("UNHCR","unhcr_source_status.csv","unhcr","data/raw/unhcr_forced_displacement_focus.csv.gz","numeric_download","PopStatsOfficial forced-displacement/statelessness populations; not voluntary migration flows.","persons"),
    ("UN DESA","undesa_source_status.csv","undesa","data/raw/undesa_migrant_stock_long.csv","numeric_download","International Migrant Stock 2024; stock at reference years, not annual flows.","persons")]
    for publisher,status_name,snap_source,output_rel,source_type,definition,default_unit in configs:
        st_df=read_csv(META/status_name); data_path=ROOT/output_rel; data=read_csv(data_path)
        for st in st_df.to_dict("records") if not st_df.empty else []:
            dataset=first(st,"indicator","dataset","table_type","source_dataset","direction",default=publisher)
            if publisher=="UN DESA":
                sid=first(st,"source_id")
                suffix=sid.rsplit("_",1)[-1].lower() if sid else ""
                dataset=suffix if suffix in {"destination","origin","bilateral"} else first(st,"dataset",default=publisher)
            g=data
            if publisher=="ILOSTAT" and not data.empty and "indicator" in data.columns:
                code=first(st,"indicator","indicator_code")
                if code: g=data[data["indicator"].astype(str).eq(code)]
            elif publisher=="UN DESA" and not data.empty and "direction" in data.columns:
                direction=dataset
                g=data[data["direction"].astype(str).eq(direction)]
            n,missing,miss=numeric_stats(g,["OBS_VALUE","obs_value","migrant_stock_persons","value","population"])
            dup=natural_duplicates(g,publisher); status=first(st,"status",default="UNKNOWN")
            url=first(st,"url","data_url","download_url")
            snap_tokens=None
            if publisher=="UN DESA":
                snap_tokens={"destination":["by_sex_and_destination"],"origin":["by_sex_and_origin"],"bilateral":["destination_and_origin"]}.get(dataset)
            snap=snapshot_for(snap_source,snap_tokens,first(st,"raw_snapshot_path","download_path","snapshot_path"))
            sh=first(st,"sha256_response","sha256_full_export","source_data_sha256","sha256","source_sha256") or (sha256_file(snap) if snap else "")
            label=first(st,"indicator_label_expected","dataset","table_type","indicator",default=dataset)
            obs_start=first(st,"observation_start"); obs_end=first(st,"observation_end","observation_end_requested")
            if publisher=="UN DESA":
                yrs=re.findall(r"\d{4}",first(st,"observation_years"))
                if n and "year" in g.columns:
                    numeric_years=pd.to_numeric(g["year"],errors="coerce").dropna()
                    if len(numeric_years): yrs=[str(int(numeric_years.min())),str(int(numeric_years.max()))]
                if yrs: obs_start,obs_end=min(yrs),max(yrs)
            if n and publisher=="ILOSTAT" and "time" in g.columns:
                yrs=pd.to_numeric(g["time"].astype(str).str.slice(0,4),errors="coerce").dropna()
                if len(yrs): obs_start,obs_end=str(int(yrs.min())),str(int(yrs.max()))
            if n and publisher=="OECD" and "TIME_PERIOD" in g.columns:
                yrs=pd.to_numeric(g["TIME_PERIOD"].astype(str).str.slice(0,4),errors="coerce").dropna()
                if len(yrs): obs_start,obs_end=str(int(yrs.min())),str(int(yrs.max()))
            unit=first(st,"unit","unit_label",default=default_unit)
            if publisher=="ILOSTAT": unit="thousands" if "thousand" in label.lower() else default_unit
            if publisher=="UN DESA": release="2024 dataset release; exact publication date not exposed by status file"
            else: release=first(st,"release_date","api_lastupdated",default="not exposed by endpoint")
            defn=label if publisher=="ILOSTAT" else definition
            geo=first(st,"geographies_fetched","countries_fetched",default="focus/global subset")
            rows.append(blank_row(workflow_id,etl_run_id,etl_outcome,
                source_id=f"{publisher}:{dataset}",publisher=publisher,source_type=source_type,dataset_id=dataset,
                exact_url=url,request_urls_json=json.dumps([url]) if url else "",
                metadata_url=first(st,"metadata_url","catalogue_url"),
                retrieval_timestamp_utc=first(st,"checked_at_utc","retrieved_utc","retrieved_at_utc","retrieval_timestamp_utc",default=etl_run_id),
                publication_release_date=release,observation_period_start=obs_start,
                observation_period_end_requested=first(st,"observation_end_requested"),observation_period_end_observed=obs_end,
                definition=defn,unit=unit,geography_scope=geo,
                origin_scope=first(st,"origin_scope","origin",default="preserved in source dimensions where available"),
                destination_scope=first(st,"destination_scope","destination",default="focus destination or source geography"),
                cohort=first(st,"sex","cohort","classif1",default="source-defined; dimensions preserved"),
                revision_vintage=sh,fetch_status=status,http_status=first(st,"http_status",default="200" if success(status) else ""),
                rows_fetched=as_int(first(st,"rows_fetched","source_rows"),n),
                rows_normalized=as_int(first(st,"rows_focus","focus_rows"),n),rows_rejected="",
                duplicate_rows=dup,missing_values=missing,missingness_pct=miss,sha256=sh,
                raw_snapshot_path=rel(snap) if snap else first(st,"raw_snapshot_path","download_path"),
                normalized_output_path=rel(data_path),counted_in_numeric_totals="true",
                validation_status="PASS" if dup==0 else "WARN",error=first(st,"error"),
                notes=definition+" Raw snapshots are retained; per-row revision ledger not yet implemented."
            ))
    ob=read_csv(META/"obmigra_source_status.csv")
    for st in ob.to_dict("records") if not ob.empty else []:
        url=first(st,"url","final_url"); status=first(st,"status",default="UNKNOWN")
        snap=snapshot_for("obmigra",None,first(st,"raw_snapshot_path"))
        rows.append(blank_row(workflow_id,etl_run_id,etl_outcome,
            source_id="OBMigra:official_page_monitor",publisher="OBMigra / Brazilian government migration observatory",
            source_type="catalogue_page_monitor",dataset_id="official migration statistics page",exact_url=url,
            request_urls_json=json.dumps([url]) if url else "",retrieval_timestamp_utc=first(st,"checked_at_utc","retrieved_utc","retrieved_at_utc","retrieval_timestamp_utc",default=etl_run_id),
            publication_release_date="not applicable",definition="Official catalogue/page monitor only; no numeric table ingestion from this page.",
            unit="not applicable",geography_scope="Brazil",revision_vintage=first(st,"content_sha256"),
            fetch_status=status,http_status=first(st,"http_status"),rows_fetched=0,rows_normalized=0,
            sha256=first(st,"content_sha256") or sha256_file(snap),raw_snapshot_path=rel(snap) if snap else "",
            counted_in_numeric_totals="false",validation_status="PASS" if success(status,first(st,"http_status")) else "WARN",
            error=first(st,"error"),notes="Page monitoring is not numeric data ingestion."
        ))
    policy=read_csv(META/"policy_page_watch_status.csv")
    for st in policy.to_dict("records") if not policy.empty else []:
        url=first(st,"url","final_url"); status=first(st,"status",default="UNKNOWN")
        token=hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] if url else ""
        snap=snapshot_for("policy_pages",[token]) if token else None
        rows.append(blank_row(workflow_id,etl_run_id,etl_outcome,
            source_id=f"PolicyPage:{first(st,'country',default='unknown')}:{first(st,'source_label','label',default='official page')}",
            publisher=first(st,"source_label","label",default="official immigration authority"),source_type="policy_page_monitor",
            dataset_id=first(st,"source_label","label"),exact_url=url,request_urls_json=json.dumps([url]) if url else "",
            retrieval_timestamp_utc=first(st,"checked_at_utc","retrieved_utc","retrieved_at_utc","retrieval_timestamp_utc",default=etl_run_id),
            publication_release_date="not extracted; manual event review required",
            observation_period_start=first(st,"checked_at_utc"),observation_period_end_observed=first(st,"checked_at_utc"),
            definition="Official policy/news page hash monitor; a hash change is a review trigger, not a confirmed policy event.",
            unit="not applicable",geography_scope=first(st,"country"),destination_scope=first(st,"country"),
            cohort="policy applicants/workers/students only if a specific event is later verified",
            revision_vintage=first(st,"content_sha256"),fetch_status=status,http_status=first(st,"http_status"),
            rows_fetched=0,rows_normalized=0,sha256=first(st,"content_sha256") or sha256_file(snap),
            raw_snapshot_path=rel(snap) if snap else "",normalized_output_path=rel(META/"policy_page_watch_status.csv"),
            counted_in_numeric_totals="false",validation_status="PASS" if success(status,first(st,"http_status")) else "WARN",
            error=first(st,"error"),notes="No policy event or causal effect is inferred from a page hash."
        ))
    brazil_path=ROOT/"data"/"raw"/"brazil_world_bank_macro.csv"; brazil=read_csv(brazil_path)
    if not brazil.empty:
        dup=natural_duplicates(brazil,"Brazil WDI")
        years=pd.to_numeric(brazil["year"],errors="coerce") if "year" in brazil.columns else pd.Series(dtype=float)
        rows.append(blank_row(workflow_id,etl_run_id,etl_outcome,
            source_id="Derived:Brazil_WDI_subset",publisher="World Bank",source_type="derived_subset",
            dataset_id="Brazil subset of WDI panel",exact_url="multiple WDI indicator endpoints; see WDI indicator rows",
            publication_release_date="inherits WDI vintages; see indicator rows",
            observation_period_start=str(int(years.min())) if len(years.dropna()) else "",
            observation_period_end_observed=str(int(years.max())) if len(years.dropna()) else "",
            definition="Country-year subset extracted from the broad WDI panel; not a separate source request.",
            unit="multiple indicator-specific units",geography_scope="Brazil (BRA)",destination_scope="Brazil (BRA)",
            fetch_status="DERIVED",rows_fetched=0,rows_normalized=len(brazil),duplicate_rows=dup,
            normalized_output_path=rel(brazil_path),counted_in_numeric_totals="false",
            validation_status="PASS" if dup==0 else "FAIL",
            notes="Derived subset; excluded from numeric source totals to avoid double counting."
        ))
    panel_rows=len(panel)
    panel_missing=int(panel["value_num"].isna().sum()) if panel_rows and "value_num" in panel.columns else 0
    panel_dup=natural_duplicates(panel,"WDI") if panel_rows else 0
    years=pd.to_numeric(panel["year"],errors="coerce").dropna() if panel_rows and "year" in panel.columns else pd.Series(dtype=float)
    numeric_fetched=sum(as_int(r.get("rows_fetched")) for r in rows if r.get("counted_in_numeric_totals")=="true" and r.get("source_type") in {"numeric_api","numeric_download"})
    numeric_normalized=sum(as_int(r.get("rows_normalized")) for r in rows if r.get("counted_in_numeric_totals")=="true" and r.get("source_type") in {"numeric_api","numeric_download"})
    failures=sum(1 for r in rows if r.get("source_type") not in {"derived_subset"} and r.get("fetch_status") and not success(r.get("fetch_status",""),r.get("http_status","")))
    dup_total=sum(as_int(r.get("duplicate_rows")) for r in rows if r.get("duplicate_rows")!="")
    rebuild=read_json(META/"wdi_history_rebuild_manifest.json")
    output=OUT/"source_retrieval_audit.csv"
    with output.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    lineage_path=META/"source_lineage_current.csv"
    with lineage_path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=LINEAGE_FIELDS); writer.writeheader()
        writer.writerows({k:r.get(k,"") for k in LINEAGE_FIELDS} for r in rows)
    legacy_lineage=META/"source_lineage_2026-10-13.csv"
    legacy_lineage_rows=len(read_csv(legacy_lineage)) if legacy_lineage.exists() else 0
    workflow_path=ROOT/".github"/"workflows"/"eom-daily-refresh.yml"
    workflow_text=workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
    schedule_match=re.search(r"""^\s*-\s*cron:\s*["']([^"']+)["']""",workflow_text,re.MULTILINE)
    scheduled_cron=schedule_match.group(1) if schedule_match else "not found"
    manifest={
    "workflow_run_id":workflow_id,"etl_run_id":etl_run_id,"etl_outcome":etl_outcome,
    "workflow_event":os.environ.get("GITHUB_EVENT_NAME","unknown"),"scheduled_cron_utc":scheduled_cron,
    "refresh_manifest_matches_workflow_run":manifest_current,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
    "source_records":len(rows),"source_failures_or_unknown_status":failures,
    "numeric_source_rows_fetched_sum_across_endpoints":numeric_fetched,
    "numeric_normalized_rows_sum_across_primary_datasets":numeric_normalized,
    "derived_rows_excluded_from_numeric_totals":True,"panel_rows":panel_rows,
    "panel_indicators":int(panel["indicator_code"].nunique()) if panel_rows and "indicator_code" in panel.columns else 0,
    "panel_geographies":int(panel["country_code"].nunique()) if panel_rows and "country_code" in panel.columns else 0,
    "panel_iso3_geographies":int(panel.loc[panel["country_code_type"].astype(str).eq("ISO3"),"country_code"].nunique()) if panel_rows and "country_code_type" in panel.columns else 0,
    "panel_duplicate_natural_keys":panel_dup,"panel_missing_values":panel_missing,
    "panel_missingness_pct":round(panel_missing/panel_rows*100,4) if panel_rows else None,
    "panel_year_start":int(years.min()) if len(years) else None,"panel_year_end":int(years.max()) if len(years) else None,
    "wdi_history_rows":as_int(refresh.get("world_bank_history_rows")),
    "wdi_history_new_keys":as_int(refresh.get("world_bank_history_new_keys")),
    "wdi_history_value_revisions":as_int(refresh.get("world_bank_history_value_revisions")),
    "wdi_history_unchanged_rows_skipped":as_int(refresh.get("world_bank_history_unchanged_rows_skipped")),
    "wdi_history_duplicates":as_int(refresh.get("world_bank_history_duplicate_keys")),
    "one_time_wdi_history_rows_restored_from_snapshots":as_int(rebuild.get("rows_restored_vs_legacy_history")),
    "natural_key_duplicate_rows_across_audited_tables":dup_total,
    "validation_status":"PASS_WITH_WARNINGS" if failures or panel_dup or dup_total else "PASS",
    "revision_tracking_note":"The compact WDI ledger is versioned. Supplemental sources retain raw snapshots/current extracts; per-row revision ledgers are not yet implemented for every supplemental source.",
    "source_lineage_current_path":str(lineage_path.relative_to(ROOT)),"source_lineage_current_rows":len(rows),
    "source_lineage_current_sha256":sha256_file(lineage_path),
    "legacy_source_lineage_registry_path":str(legacy_lineage.relative_to(ROOT)) if legacy_lineage.exists() else "",
    "legacy_source_lineage_registry_rows":legacy_lineage_rows,
    "legacy_source_lineage_registry_status":"preserved_legacy_registry" if legacy_lineage.exists() else "not_found",
    "output_path":str(output.relative_to(ROOT)),"output_sha256":sha256_file(output)}
    (META/"source_audit_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(manifest,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
