#!/usr/bin/env python3
"""Change-driven EOM recomputation gate: daily retrieval continues; model fits run only on material input/specification changes."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/"metadata"; OUT=ROOT/"outputs"
STATE_PATH=META/"recompute_state.json"
WDI_PATH=ROOT/"data/raw/world_bank_macro_focus.csv"
OECD_PATH=ROOT/"data/observations_history/oecd_imo_2026_a_series_history.csv"
BILATERAL_PATH=ROOT/"data/bilateral/eurostat_od_flows_history.csv.gz"
FEATURES=["salary_proxy","cost_proxy","opportunity_proxy","policy_proxy","institution_proxy","stability_proxy"]
OECD_MEASURES={"immigration_foreign_population","foreign_born_population_share","acquisitions_share_of_foreign_population"}
CODE_GROUPS={
 "primary":["src/eom_empirical/model.py","src/eom_empirical/fit_macro_model.py","data/destinations.csv","RESEARCH_PROGRAM.md"],
 "backtest":["src/eom_empirical/model.py","src/eom_empirical/fit_macro_model.py","src/eom_empirical/evaluation.py","data/destinations.csv","RESEARCH_PROGRAM.md"],
 "oecd":["src/eom_empirical/model.py","src/eom_empirical/oecd_macro.py","data/destinations.csv","RESEARCH_PROGRAM.md"],
 "bilateral":["src/eom_empirical/model.py","src/eom_empirical/evaluation.py","src/eom_empirical/bilateral_gravity.py","scripts/run_bilateral_gravity_benchmark.py","data/destinations.csv","RESEARCH_PROGRAM.md"],
}

def now(): return datetime.now(timezone.utc).isoformat()
def sha_text(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def read_json(p):
 try: return json.loads(p.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): return {}
def write_json(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def canonical_hash(df,cols,keys,numeric):
 x=df[cols].copy()
 for c in numeric:
  x[c]=pd.to_numeric(x[c],errors="coerce").map(lambda v:"" if pd.isna(v) else format(float(v),".15g"))
 for c in cols:
  if c not in numeric: x[c]=x[c].fillna("").astype(str)
 x=x.sort_values(keys,kind="mergesort").reset_index(drop=True)
 return sha_text(x.to_csv(index=False,na_rep="",lineterminator="\n"))
def git_blob_sha(p):
 data=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()
def code_signature(group):
 parts=[]
 for rel in sorted(CODE_GROUPS[group]):
  p=ROOT/rel
  if not p.exists(): return "MISSING"
  parts.append(f"{rel}:{git_blob_sha(p)}")
 return sha_text("\n".join(parts)+"\n")
def load_wdi_wide():
 if not WDI_PATH.exists(): raise FileNotFoundError(f"Missing scoring input {WDI_PATH}")
 from eom_empirical.model import to_wide,add_derived_features
 long=pd.read_csv(WDI_PATH,low_memory=False)
 required={"country_code","year","indicator_code","value"}
 if not required.issubset(long.columns): raise ValueError(f"Scoring input missing columns {sorted(required-set(long.columns))}")
 if long.duplicated(["country_code","indicator_code","year"]).any(): raise ValueError("Duplicate country-indicator-year natural keys in scoring input")
 long["year"]=pd.to_numeric(long["year"],errors="coerce")
 wide=add_derived_features(to_wide(long))
 destinations=pd.read_csv(ROOT/"data/destinations.csv",dtype=str).fillna("")
 codes=set(destinations.loc[destinations.primary_choice_set.eq("global_country"),"wb_country_code"].dropna())-{""}
 wide=wide[wide.country_code.isin(codes)].copy()
 wide["year"]=pd.to_numeric(wide.year,errors="coerce")
 return wide
def geodist_sha_from_audit():
 audit=read_json(META/"bilateral_gravity_data_audit.json")
 for source in audit.get("sources",[]):
  if str(source.get("publisher","")).lower()=="cepii":
   if source.get("raw_sha256"): return str(source["raw_sha256"])
   parts=[source.get("rows"),source.get("distance_field"),source.get("raw_zip_size_bytes"),source.get("raw_xls_size_bytes")]
   if any(v is not None for v in parts): return "legacy-fingerprint:"+sha_text("|".join(map(str,parts)))
 return None
def bilateral_flow_signature():
 if not BILATERAL_PATH.exists(): return None
 f=pd.read_csv(BILATERAL_PATH,compression="gzip",low_memory=False)
 cols=["dataset","origin_iso3","destination_iso3","year","record_hash","revision_number","revision_type","flow_persons","observation_status","source_flag","unit"]
 if not set(cols).issubset(f.columns): raise ValueError("Bilateral flow history lacks expected natural-key/revision columns")
 return canonical_hash(f,cols,["dataset","origin_iso3","destination_iso3","year","revision_number"],["year","revision_number","flow_persons"])
def signatures():
 wide=load_wdi_wide()
 coverage=wide.groupby("year")[FEATURES].apply(lambda g:g.notna().all(axis=1).sum())
 eligible=coverage[coverage>=10]
 if eligible.empty: raise ValueError("No year has at least 10 complete destination rows")
 latest=int(eligible.index.max())
 primary=wide[wide.year.eq(latest)].copy()
 primary_hash=canonical_hash(primary,["country_code","year",*FEATURES],["country_code","year"],["year",*FEATURES])
 backtest_hash=canonical_hash(wide,["country_code","year",*FEATURES,"net_migration_per_1000"],["country_code","year"],["year",*FEATURES,"net_migration_per_1000"])
 if not OECD_PATH.exists():
  oecd_hash="MISSING"; oecd_rows=0; pop_hash="MISSING"
 else:
  o=pd.read_csv(OECD_PATH,low_memory=False)
  required={"table_code","destination","origin","measure","year","value","unit","observation_status","retrieved_at_utc"}
  if not required.issubset(o.columns): raise ValueError(f"OECD history missing columns {sorted(required-set(o.columns))}")
  o["year"]=pd.to_numeric(o.year,errors="coerce"); o["value"]=pd.to_numeric(o.value,errors="coerce")
  o=o[o.measure.isin(OECD_MEASURES)&o.observation_status.eq("observed")&o.value.notna()].copy()
  nk=["table_code","destination","origin","measure","year"]
  o=o.sort_values("retrieved_at_utc").drop_duplicates(nk,keep="last")
  oecd_hash=canonical_hash(o,[*nk,"value","unit","observation_status"],nk,["year","value"])
  oecd_rows=len(o)
  pop=wide[["country_code","year","SP.POP.TOTL"]].copy()
  pop_hash=canonical_hash(pop,["country_code","year","SP.POP.TOTL"],["country_code","year"],["year","SP.POP.TOTL"])
 return {
  "primary":{"input_sha256":primary_hash,"code_sha256":code_signature("primary"),"latest_year":latest,"rows":len(primary)},
  "backtest":{"input_sha256":backtest_hash,"code_sha256":code_signature("backtest"),"rows":len(wide)},
  "oecd":{"input_sha256":sha_text("|".join([oecd_hash,pop_hash,primary_hash])),"oecd_feature_sha256":oecd_hash,"population_sha256":pop_hash,"code_sha256":code_signature("oecd"),"rows":oecd_rows},
  "bilateral":{"flow_history_sha256":bilateral_flow_signature(),"geodist_sha256":geodist_sha_from_audit(),"code_sha256":code_signature("bilateral")},
 }
def bootstrap():
 if STATE_PATH.exists(): return read_json(STATE_PATH)
 manifest=read_json(META/"macro_ranking_delta_manifest.json")
 if str(manifest.get("recompute_outcome","")).lower()!="success": raise RuntimeError("Cannot bootstrap: latest stored primary ranking was not successfully recomputed")
 for p in [OUT/"latest_macro_eom_ranking.csv",OUT/"latest_oecd_enhanced_macro_ranking.csv"]:
  if not p.exists() or p.stat().st_size==0: raise RuntimeError(f"Cannot bootstrap: missing validated output {p.relative_to(ROOT)}")
 s=signatures(); bilateral=read_json(OUT/"bilateral_gravity_benchmark.json")
 state={"schema_version":1,"bootstrapped_at_utc":now(),"bootstrap_reason":"Input/code fingerprints captured from the latest verified successful primary and OECD-enhanced rankings before change-driven gating.",
 "baseline_workflow_run_id":str(manifest.get("workflow_run_id","")),
 "baseline_workflow_url":f"https://github.com/schnozenstein/eom-migration-model/actions/runs/{manifest.get('workflow_run_id','')}",
 "last_successful":{
  "primary":{**s["primary"],"workflow_run_id":str(manifest.get("workflow_run_id",""))},
  "backtest":{**s["backtest"],"workflow_run_id":str(manifest.get("workflow_run_id",""))},
  "oecd":{**s["oecd"],"workflow_run_id":str(manifest.get("workflow_run_id",""))},
  "bilateral":{**s["bilateral"],"workflow_run_id":str(bilateral.get("retrieval_run_id","")),"benchmark_status":bilateral.get("status","unknown")},
 },"last_checked_at_utc":now()}
 write_json(STATE_PATH,state); return state
def emit_outputs(values):
 path=os.environ.get("GITHUB_OUTPUT")
 if path:
  with open(path,"a",encoding="utf-8") as f:
   for k,v in values.items(): f.write(f"{k}={v}\n")
def evaluate():
 state=read_json(STATE_PATH) or bootstrap(); last=state.get("last_successful",{})
 scoring_outcome=str(os.environ.get("EOM_SCORING_INPUT_OUTCOME","success")).lower()
 if scoring_outcome!="success":
  result={"status":"blocked_scoring_input_refresh_failed","skip_reason":"scoring_input_refresh_failed; model calculations skipped rather than using stale scoring inputs",
   "primary_changed":False,"backtest_changed":False,"oecd_changed":False,"bilateral_code_changed":False,"recompute_required":False,"scoring_input_outcome":scoring_outcome}
 else:
  cur=signatures(); pr=[]; br=[]; ore=[]
  if cur["primary"]["input_sha256"]!=last.get("primary",{}).get("input_sha256"): pr.append("latest_year_scoring_values_changed")
  if cur["primary"]["code_sha256"]!=last.get("primary",{}).get("code_sha256"): pr.append("primary_model_or_destination_specification_changed")
  if cur["backtest"]["input_sha256"]!=last.get("backtest",{}).get("input_sha256"): br.append("historical_features_or_matured_migration_outcomes_changed")
  if cur["backtest"]["code_sha256"]!=last.get("backtest",{}).get("code_sha256"): br.append("backtest_or_evaluation_specification_changed")
  if cur["oecd"]["input_sha256"]!=last.get("oecd",{}).get("input_sha256"): ore.append("OECD_A1_A4_A6_or_WDI_population_inputs_changed")
  if cur["oecd"]["code_sha256"]!=last.get("oecd",{}).get("code_sha256"): ore.append("OECD_enhanced_model_specification_changed")
  if pr: ore.append("primary_WDI_baseline_changed")
  bc=cur["bilateral"]["code_sha256"]!=last.get("bilateral",{}).get("code_sha256")
  pc=bool(pr); bkc=bool(br); oc=bool(ore)
  result={"status":"material_change_detected" if (pc or bkc or oc or bc) else "no_material_change",
   "skip_reason":"" if (pc or bkc) else "no_new_validated_primary_scoring_or_backtest_values_or_model_change",
   "primary_changed":pc,"primary_reasons":pr,"backtest_changed":bkc,"backtest_reasons":br,
   "oecd_changed":oc,"oecd_reasons":ore,"bilateral_code_changed":bc,"recompute_required":pc or bkc or oc or bc,
   "scoring_input_outcome":scoring_outcome,"current_signatures":cur,"baseline_run_id":state.get("baseline_workflow_run_id")}
 result.update({"workflow_run_id":str(os.environ.get("GITHUB_RUN_ID","")),"generated_at_utc":now()})
 write_json(META/"recompute_gate.json",result)
 emit_outputs({k:str(bool(result.get(src))).lower() for k,src in [
  ("primary_changed","primary_changed"),("backtest_changed","backtest_changed"),("oecd_changed","oecd_changed"),
  ("bilateral_code_changed","bilateral_code_changed"),("recompute_required","recompute_required")]})
 emit_outputs({"skip_reason":str(result.get("skip_reason",""))})
 print(json.dumps(result,indent=2)); return result
def finalize():
 state=read_json(STATE_PATH)
 if not state: raise RuntimeError("Cannot finalize: recompute state missing")
 cur=signatures(); run_id=str(os.environ.get("GITHUB_RUN_ID",""))
 po=str(os.environ.get("EOM_PRIMARY_OUTCOME","skipped")).lower()
 oo=str(os.environ.get("EOM_OECD_OUTCOME","skipped")).lower()
 bo=str(os.environ.get("EOM_BILATERAL_OUTCOME","skipped")).lower()
 if po=="success":
  state["last_successful"]["primary"]={**cur["primary"],"workflow_run_id":run_id}
  state["last_successful"]["backtest"]={**cur["backtest"],"workflow_run_id":run_id}
 if oo=="success": state["last_successful"]["oecd"]={**cur["oecd"],"workflow_run_id":run_id}
 if bo=="success":
  audit=read_json(META/"bilateral_gravity_data_audit.json"); status=str(audit.get("status","")).lower()
  if status in {"completed","skipped_no_material_change","skipped_no_material_change_source_unavailable"}:
   b=dict(cur["bilateral"]); b["geodist_sha256"]=geodist_sha_from_audit() or state["last_successful"].get("bilateral",{}).get("geodist_sha256")
   b.update({"workflow_run_id":run_id,"benchmark_status":status}); state["last_successful"]["bilateral"]=b
 state["last_checked_at_utc"]=now(); state["last_workflow_run_id"]=run_id
 state["last_outcomes"]={"primary":po,"oecd":oo,"bilateral":bo}
 write_json(STATE_PATH,state); print(json.dumps({"state_path":str(STATE_PATH.relative_to(ROOT)),"last_outcomes":state["last_outcomes"]},indent=2))
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("command",choices=["bootstrap","evaluate","finalize"]); a=p.parse_args()
 if a.command=="bootstrap": print(json.dumps(bootstrap(),indent=2))
 elif a.command=="evaluate": evaluate()
 else: finalize()
if __name__=="__main__": main()
