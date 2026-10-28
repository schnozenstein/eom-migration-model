#!/usr/bin/env python3
"""Create a conservative policy-page delta; content hashes are not policy events."""
from __future__ import annotations
import argparse,csv,json,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; META=ROOT/"metadata"; OUT=ROOT/"outputs"
FIELDS=["workflow_run_id","etl_run_id","country","publisher_or_page_label","source_url","final_url","retrieval_timestamp_utc","fetch_status","http_status","previous_content_sha256","current_content_sha256","content_hash_changed","event_status","confirmed_policy_event","event_type","announcement_date","effective_date","affected_cohort","mechanism","counterfactual_design","causal_estimate_status","notes"]
def norm_http(value):
    try: return str(int(float(str(value).strip())))
    except Exception: return str(value or "").strip()
def read_json(path):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:return {}
def read_rows(path):
    p=Path(path)
    if not p.exists():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def build_policy_delta(previous_state,current_rows,workflow_run_id="",etl_outcome="success",etl_run_id=""):
    rows=[]; baseline=isinstance(previous_state,dict) and bool(previous_state)
    for st in current_rows:
        url=(st.get("url") or "").strip(); final=(st.get("final_url") or "").strip()
        previous=previous_state.get(url) or previous_state.get(final) or {}
        old=str(previous.get("content_sha256","") or ""); new=str(st.get("content_sha256","") or "")
        status=str(st.get("status","UNKNOWN") or "UNKNOWN").upper(); http=norm_http(st.get("http_status",""))
        good=status in {"SUCCESS","OK","PASS","200"} and (not http or http=="200") and bool(new)
        changed=bool(old and new and old!=new)
        if str(etl_outcome).lower()!="success":
            event_status="UNKNOWN_ETL_FAILED"; note="Full ETL did not complete; page status cannot be treated as a current policy check."
        elif not good:
            event_status="UNKNOWN_FETCH_FAILED"; note="Official page fetch failed or returned no current hash; do not infer policy unchanged."
        elif not old:
            event_status="FIRST_SEEN_BASELINE_MISSING"; note="No prior content hash available; manual review is required."
        elif changed:
            event_status="CONTENT_CHANGED_REVIEW_REQUIRED"; note="Content hash changed. This is a review trigger only; dynamic page content may change without a policy change."
        else:
            event_status="NO_HASH_CHANGE"; note="No content hash change detected; this does not prove no policy change elsewhere."
        rows.append({"workflow_run_id":workflow_run_id,"etl_run_id":etl_run_id,"country":st.get("country",""),
        "publisher_or_page_label":st.get("source_label") or st.get("label",""),"source_url":url,"final_url":final,
        "retrieval_timestamp_utc":st.get("checked_at_utc",""),"fetch_status":status,"http_status":http,
        "previous_content_sha256":old,"current_content_sha256":new,"content_hash_changed":str(changed).lower(),
        "event_status":event_status,"confirmed_policy_event":"false","event_type":"","announcement_date":"",
        "effective_date":"","affected_cohort":"","mechanism":"","counterfactual_design":"",
        "causal_estimate_status":"not_assessed","notes":note})
    return rows,baseline
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--previous-state",required=True); args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True); META.mkdir(parents=True,exist_ok=True)
    workflow_id=str(os.environ.get("GITHUB_RUN_ID","")); etl_outcome=str(os.environ.get("EOM_ETL_OUTCOME","unknown")).lower()
    manifests=sorted((META/"refresh_runs").glob("*.json")); refresh=read_json(manifests[-1]) if manifests else {}
    etl_run_id=str(refresh.get("run_id","")); previous=read_json(args.previous_state)
    rows,baseline=build_policy_delta(previous,read_rows(META/"policy_page_watch_status.csv"),workflow_id,etl_outcome,etl_run_id)
    out=OUT/"policy_event_delta.csv"
    with out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    counts={}
    for r in rows: counts[r["event_status"]]=counts.get(r["event_status"],0)+1
    manifest={"workflow_run_id":workflow_id,"etl_run_id":etl_run_id,"etl_outcome":etl_outcome,
    "generated_at_utc":datetime.now(timezone.utc).isoformat(),"baseline_available":baseline,"policy_pages_checked":len(rows),
    "content_changed_pages":counts.get("CONTENT_CHANGED_REVIEW_REQUIRED",0),"unchanged_pages":counts.get("NO_HASH_CHANGE",0),
    "failed_or_unknown_pages":counts.get("UNKNOWN_FETCH_FAILED",0)+counts.get("UNKNOWN_ETL_FAILED",0),
    "first_seen_pages":counts.get("FIRST_SEEN_BASELINE_MISSING",0),"confirmed_policy_events":0,"causal_estimates":0,
    "event_status_counts":counts,"interpretation":"Page hash changes are not verified policy events. No event is confirmed until a specific official notice, announcement/effective date, affected cohort and mechanism are extracted and reviewed.",
    "output_path":str(out.relative_to(ROOT))}
    (META/"policy_event_delta_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
