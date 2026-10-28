#!/usr/bin/env python3
"""Maintain a versioned national migration outcome ledger and production forecast ledger."""
from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; META=ROOT/"metadata"
PREDICTION_COLUMNS=["forecast_id","issue_date","target","target_period","horizon","geography_id","geography_name","model_version","point_forecast","lower_bound","upper_bound","uncertainty_method","assumptions","data_cutoff","source_vintage","calibration_status","validation_status","issued_by_run_id","status","notes"]
OUTCOME_COLUMNS=["target","geography_id","geography_name","observation_period","value","unit","source","source_urls_json","source_vintage","recorded_at_utc","revision_id","revision_type","observation_definition","geography_level","origin","destination","cohort","quality_flag","notes"]
JOIN_COLUMNS=["forecast_id","issue_date","target","target_period","horizon","geography_id","geography_name","model_version","forecast_value","outcome_value","outcome_vintage","outcome_recorded_at_utc","signed_error_outcome_minus_forecast","absolute_error","join_status","data_cutoff"]
def read_frame(path,columns):
    if not path.exists() or path.stat().st_size==0:return pd.DataFrame(columns=columns)
    df=pd.read_csv(path,dtype=str,keep_default_na=False,low_memory=False)
    for c in columns:
        if c not in df.columns:df[c]=""
    return df[columns]
def write_frame(df,path,columns):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    df.reindex(columns=columns).to_csv(tmp,index=False); tmp.replace(path)
def revision_id(target,geo,period,value,vintage):
    raw="|".join([str(target),str(geo),str(period),format(float(value),".12g"),str(vintage)])
    return hashlib.sha256(raw.encode()).hexdigest()[:20]
def derive_current_outcomes(panel,recorded_at_utc,exact_urls=None):
    if panel.empty:return pd.DataFrame(columns=OUTCOME_COLUMNS)
    required={"country_code","country_code_type","country_name_api","indicator_code","year","value"}
    if not required.issubset(panel.columns):raise ValueError(f"WDI panel missing columns: {sorted(required-set(panel.columns))}")
    p=panel.copy(); p["year"]=pd.to_numeric(p["year"],errors="coerce"); p["value_num"]=pd.to_numeric(p["value"],errors="coerce")
    p=p[p["country_code_type"].astype(str).eq("ISO3") & p["indicator_code"].astype(str).isin(["SM.POP.NETM","SP.POP.TOTL"])]
    net=p[p["indicator_code"].astype(str).eq("SM.POP.NETM")]; pop=p[p["indicator_code"].astype(str).eq("SP.POP.TOTL")]
    key=["country_code","year"]
    if net.duplicated(key).any() or pop.duplicated(key).any():raise ValueError("Duplicate WDI natural key for net migration or population")
    cols=key+["country_name_api","value_num","api_lastupdated","source_url"]
    net=net[[c for c in cols if c in net.columns]].rename(columns={"country_name_api":"name_net","value_num":"net_migration","api_lastupdated":"vintage_net","source_url":"url_net"})
    pop=pop[[c for c in cols if c in pop.columns]].rename(columns={"country_name_api":"name_pop","value_num":"population","api_lastupdated":"vintage_pop","source_url":"url_pop"})
    joined=net.merge(pop,on=key,how="inner").dropna(subset=["net_migration","population"])
    joined=joined[joined["population"]>0]; exact_urls=exact_urls or {}; rows=[]
    for r in joined.to_dict("records"):
        year=int(r["year"]); val=float(r["net_migration"])/float(r["population"])*1000.0
        vintage=max([str(r.get(k,"") or "") for k in ["vintage_net","vintage_pop"] if str(r.get(k,"") or "") not in ("","nan")],default="not_reported")
        urls={"SM.POP.NETM":exact_urls.get("SM.POP.NETM",str(r.get("url_net","") or "")),"SP.POP.TOTL":exact_urls.get("SP.POP.TOTL",str(r.get("url_pop","") or ""))}
        target="national_net_migration_per_1000"
        rows.append({"target":target,"geography_id":str(r["country_code"]),"geography_name":str(r.get("name_net") or r.get("name_pop") or r["country_code"]),
        "observation_period":str(year),"value":format(val,".12g"),"unit":"net migrants per 1,000 residents","source":"World Bank WDI (derived)",
        "source_urls_json":json.dumps(urls,ensure_ascii=False,sort_keys=True),"source_vintage":vintage,"recorded_at_utc":recorded_at_utc,
        "revision_id":revision_id(target,r["country_code"],year,val,vintage),"revision_type":"initial_observation",
        "observation_definition":"SM.POP.NETM / SP.POP.TOTL * 1,000; national country-year outcome, not bilateral flow.",
        "geography_level":"country","origin":"","destination":str(r["country_code"]),"cohort":"national total; all ages/sexes as defined by WDI indicators",
        "quality_flag":"derived_country_year_fallback","notes":"Observed outcome derived from two WDI indicators; not a forecast and not a causal estimate."})
    return pd.DataFrame(rows,columns=OUTCOME_COLUMNS)
def append_outcome_versions(existing,current):
    existing=existing.reindex(columns=OUTCOME_COLUMNS).fillna(""); current=current.reindex(columns=OUTCOME_COLUMNS).fillna("")
    if not existing.empty and existing["revision_id"].astype(str).duplicated().any():raise ValueError("Duplicate outcome revision_id in persistent ledger")
    if current.empty:return existing,{"inserted":0,"revised":0,"unchanged":0,"stale":0}
    latest={}
    if not existing.empty:
        for r in existing.sort_values("recorded_at_utc").to_dict("records"):latest[(r["target"],r["geography_id"],r["observation_period"])]=r
    known=set(existing["revision_id"].astype(str)) if not existing.empty else set(); add=[]; inserted=revised=unchanged=stale=0
    for r in current.to_dict("records"):
        key=(r["target"],r["geography_id"],r["observation_period"]); old=latest.get(key)
        if old is None:r["revision_type"]="initial_observation";add.append(r);inserted+=1;known.add(r["revision_id"]);latest[key]=r;continue
        try:same_value=abs(float(old["value"])-float(r["value"]))<1e-12
        except Exception:same_value=str(old["value"])==str(r["value"])
        old_v=str(old.get("source_vintage","")); new_v=str(r.get("source_vintage",""))
        if same_value and old_v==new_v:unchanged+=1;continue
        if old_v and new_v and new_v<old_v:stale+=1;continue
        if r["revision_id"] in known:unchanged+=1;continue
        r["revision_type"]="value_revision" if not same_value else "source_vintage_revision"
        add.append(r);revised+=1;known.add(r["revision_id"]);latest[key]=r
    combined=pd.concat([existing,pd.DataFrame(add,columns=OUTCOME_COLUMNS)],ignore_index=True)
    if not combined.empty and combined["revision_id"].astype(str).duplicated().any():raise ValueError("Outcome ledger would contain duplicate revision_id values")
    return combined,{"inserted":inserted,"revised":revised,"unchanged":unchanged,"stale":stale}
def validate_prediction_ledger(df):
    missing=[c for c in PREDICTION_COLUMNS if c not in df.columns]
    if missing:raise ValueError(f"Prediction ledger missing columns: {missing}")
    if df.empty:return True
    if df["forecast_id"].astype(str).duplicated().any():raise ValueError("Duplicate forecast_id")
    required=["forecast_id","issue_date","target","target_period","horizon","geography_id","model_version","data_cutoff"]
    if df[required].astype(str).apply(lambda c:c.str.strip().eq("")).any().any():raise ValueError("Prediction ledger contains blank required lineage fields")
    return True
def build_prediction_outcome_join(predictions,outcomes):
    result=[]
    if predictions.empty:return pd.DataFrame(columns=JOIN_COLUMNS)
    for p in predictions.to_dict("records"):
        target=str(p.get("target",""));geo=str(p.get("geography_id",""));period=str(p.get("target_period",""))
        matches=outcomes[(outcomes["target"].astype(str)==target)&(outcomes["geography_id"].astype(str)==geo)&(outcomes["observation_period"].astype(str)==period)] if not outcomes.empty else pd.DataFrame()
        issue=str(p.get("issue_date",""))
        if not matches.empty and "recorded_at_utc" in matches.columns:
            matured=matches[matches["recorded_at_utc"].astype(str)>=issue];matches=matured if not matured.empty else pd.DataFrame()
        if matches.empty:ov="";vintage="";recorded="";signed="";absolute="";status="OUTCOME_NOT_AVAILABLE_AFTER_ISSUE"
        else:
            o=matches.sort_values("recorded_at_utc").iloc[-1];ov=str(o["value"]);vintage=str(o.get("source_vintage",""));recorded=str(o.get("recorded_at_utc",""))
            try:
                signed=float(ov)-float(p.get("point_forecast",""));absolute=abs(signed);signed=format(signed,".12g");absolute=format(absolute,".12g");status="MATCHED"
            except Exception:signed="";absolute="";status="MATCHED_VALUE_NOT_NUMERIC"
        result.append({"forecast_id":p.get("forecast_id",""),"issue_date":issue,"target":target,"target_period":period,"horizon":p.get("horizon",""),
        "geography_id":geo,"geography_name":p.get("geography_name",""),"model_version":p.get("model_version",""),"forecast_value":p.get("point_forecast",""),
        "outcome_value":ov,"outcome_vintage":vintage,"outcome_recorded_at_utc":recorded,"signed_error_outcome_minus_forecast":signed,
        "absolute_error":absolute,"join_status":status,"data_cutoff":p.get("data_cutoff","")})
    return pd.DataFrame(result,columns=JOIN_COLUMNS)
def main():
    DATA.mkdir(parents=True,exist_ok=True);META.mkdir(parents=True,exist_ok=True)
    run_id=str(os.environ.get("GITHUB_RUN_ID",""));etl_outcome=str(os.environ.get("EOM_ETL_OUTCOME","unknown")).lower();now=datetime.now(timezone.utc).isoformat()
    pred_path=DATA/"prediction_ledger.csv";out_path=DATA/"outcome_ledger.csv";join_path=DATA/"prediction_outcome_join.csv"
    predictions=read_frame(pred_path,PREDICTION_COLUMNS);existing=read_frame(out_path,OUTCOME_COLUMNS);validate_prediction_ledger(predictions)
    panel_path=ROOT/"data"/"raw"/"world_bank_long.csv"
    panel=pd.read_csv(panel_path,low_memory=False) if panel_path.exists() and etl_outcome=="success" else pd.DataFrame()
    exact_urls={};status_path=META/"live_source_status.csv"
    if status_path.exists():
        status=pd.read_csv(status_path,dtype=str,keep_default_na=False)
        for _,r in status.iterrows():
            code=str(r.get("indicator",""))
            if code in {"SM.POP.NETM","SP.POP.TOTL"}:
                try:urls=json.loads(str(r.get("request_urls","")))
                except Exception:urls=[]
                exact_urls[code]=urls[0] if isinstance(urls,list) and urls else str(r.get("url",""))
    current=derive_current_outcomes(panel,now,exact_urls) if etl_outcome=="success" and not panel.empty else pd.DataFrame(columns=OUTCOME_COLUMNS)
    combined,stats=append_outcome_versions(existing,current);validate_prediction_ledger(predictions)
    joins=build_prediction_outcome_join(predictions,combined)
    write_frame(predictions,pred_path,PREDICTION_COLUMNS);write_frame(combined,out_path,OUTCOME_COLUMNS);write_frame(joins,join_path,JOIN_COLUMNS)
    years=pd.to_numeric(combined["observation_period"],errors="coerce").dropna() if not combined.empty else pd.Series(dtype=float)
    matched=int(joins["join_status"].eq("MATCHED").sum()) if not joins.empty else 0
    manifest={"workflow_run_id":run_id,"generated_at_utc":now,"etl_outcome":etl_outcome,"prediction_rows":len(predictions),"outcome_rows":len(combined),
    "outcome_rows_inserted":stats["inserted"],"outcome_rows_revised":stats["revised"],"outcome_rows_unchanged":stats["unchanged"],"outcome_rows_stale_skipped":stats["stale"],
    "prediction_outcome_join_rows":len(joins),"matched_outcomes":matched,"unmatched_forecasts":int(len(joins)-matched),
    "outcome_target":"national_net_migration_per_1000","outcome_unit":"net migrants per 1,000 residents","outcome_geographies":int(combined["geography_id"].nunique()) if not combined.empty else 0,
    "observation_period_start":int(years.min()) if len(years) else None,"observation_period_end":int(years.max()) if len(years) else None,
    "production_forecasts_issued_this_run":0,"parameter_fitting_performed":False,"validation_status":"PASS",
    "data_update_status":"UPDATED_FROM_CURRENT_PANEL" if etl_outcome=="success" and not panel.empty else "SKIPPED_ETL_NOT_SUCCESS",
    "interpretation":"Country-year outcome fallback derived from WDI net migration divided by population; not bilateral flow, not a forecast and not a causal estimate.",
    "prediction_ledger_path":str(pred_path.relative_to(ROOT)),"outcome_ledger_path":str(out_path.relative_to(ROOT)),"join_path":str(join_path.relative_to(ROOT))}
    (META/"prediction_ledger_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8");print(json.dumps(manifest,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
