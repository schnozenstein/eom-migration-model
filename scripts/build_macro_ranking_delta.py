#!/usr/bin/env python3
"""Record macro-ranking freshness and score/rank changes without reranking."""
from __future__ import annotations
import argparse,csv,json,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"outputs"; META=ROOT/"metadata"
FIELDS=["workflow_run_id","comparison_year","destination_id","destination_name","country_code","change_type","previous_score","current_score","score_delta","previous_rank","current_rank","rank_delta","previous_score_status","current_score_status","recompute_outcome","notes"]
def read_rows(path):
    p=Path(path)
    if not p.exists() or p.stat().st_size==0:return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def number(v):
    try:
        if str(v).strip() in ("","nan","None"):return None
        return float(v)
    except Exception:return None
def build_ranking_delta(previous,current,recompute_outcome,workflow_run_id="",code_version=""):
    pmap={str(r.get("destination_id") or r.get("country_code") or r.get("destination_name")):r for r in previous}
    cmap={str(r.get("destination_id") or r.get("country_code") or r.get("destination_name")):r for r in current}
    comparable=str(recompute_outcome).lower()=="success" and bool(previous)
    rows=[]
    for key in sorted(set(pmap)|set(cmap)):
        p=pmap.get(key); c=cmap.get(key); cur=c or {}; old=p or {}
        ps=number(old.get("energy_equal_weight")); cs=number(cur.get("energy_equal_weight"))
        pr=number(old.get("energy_rank")); cr=number(cur.get("energy_rank"))
        sd=(cs-ps) if ps is not None and cs is not None else None
        rd=(cr-pr) if pr is not None and cr is not None else None
        score_changed=ps is not None and cs is not None and abs(sd or 0)>1e-10
        rank_changed=pr is not None and cr is not None and abs(rd or 0)>1e-10
        if not comparable: kind="NOT_COMPARABLE"
        elif p is None: kind="ADDED"
        elif c is None: kind="REMOVED"
        elif score_changed and rank_changed: kind="SCORE_AND_RANK_CHANGED"
        elif score_changed: kind="SCORE_CHANGED"
        elif rank_changed: kind="RANK_CHANGED"
        elif ps is None or cs is None: kind="UNSCORED"
        else: kind="UNCHANGED"
        rows.append({"workflow_run_id":workflow_run_id,"comparison_year":cur.get("year") or old.get("year",""),
        "destination_id":key,"destination_name":cur.get("destination_name") or old.get("destination_name",""),
        "country_code":cur.get("country_code") or old.get("country_code",""),"change_type":kind,
        "previous_score":"" if ps is None else format(ps,".15g"),"current_score":"" if cs is None else format(cs,".15g"),
        "score_delta":"" if sd is None or not comparable else format(sd,".15g"),
        "previous_rank":"" if pr is None else format(pr,".15g"),"current_rank":"" if cr is None else format(cr,".15g"),
        "rank_delta":"" if rd is None or not comparable else format(rd,".15g"),
        "previous_score_status":old.get("score_status",""),"current_score_status":cur.get("score_status",""),
        "recompute_outcome":recompute_outcome,
        "notes":"Comparison is valid only when ranking recomputation succeeded and a prior ranking baseline exists; macro scores are proxies, not probabilities."})
    return rows,comparable
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--previous-ranking",required=True);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);META.mkdir(parents=True,exist_ok=True)
    run_id=str(os.environ.get("GITHUB_RUN_ID",""));sha=str(os.environ.get("GITHUB_SHA",""))
    outcome=str(os.environ.get("EOM_RANKING_RECOMPUTE_OUTCOME","unknown")).lower()
    prev=read_rows(args.previous_ranking);cur=read_rows(OUT/"latest_macro_eom_ranking.csv")
    rows,comparable=build_ranking_delta(prev,cur,outcome,run_id,sha)
    output=OUT/"macro_ranking_delta.csv"
    with output.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    changed=sum(1 for r in rows if r["change_type"] in {"SCORE_CHANGED","RANK_CHANGED","SCORE_AND_RANK_CHANGED"})
    score_changed=sum(1 for r in rows if r["change_type"] in {"SCORE_CHANGED","SCORE_AND_RANK_CHANGED"})
    rank_changed=sum(1 for r in rows if r["change_type"] in {"RANK_CHANGED","SCORE_AND_RANK_CHANGED"})
    added=sum(1 for r in rows if r["change_type"]=="ADDED");removed=sum(1 for r in rows if r["change_type"]=="REMOVED")
    scored=sum(1 for r in cur if number(r.get("energy_equal_weight")) is not None)
    years=[number(r.get("year")) for r in cur if number(r.get("year")) is not None]
    manifest={"workflow_run_id":run_id,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
    "recompute_outcome":outcome,"ranking_status":"RECOMPUTED" if outcome=="success" else "NOT_RECOMPUTED",
    "previous_ranking_available":bool(prev),"comparison_valid":comparable,"previous_rows":len(prev),"current_rows":len(cur),
    "compared_destinations":len(rows),"scored_destinations":scored,"unscored_destinations":len(cur)-scored,
    "score_changed_rows":score_changed if comparable else None,"rank_changed_rows":rank_changed if comparable else None,
    "rows_with_any_score_or_rank_change":changed if comparable else None,"added_destinations":added if comparable else None,
    "removed_destinations":removed if comparable else None,"data_cutoff":int(max(years)) if years else None,
    "scoring_version":"equal-weight macro proxy; not a calibrated migration probability",
    "code_version":sha,"output_path":str(output.relative_to(ROOT)),
    "notes":"If score/rank deltas are zero, the recomputation may still be valid; inputs and scoring dependencies must be audited before attributing stability to model quality."}
    (META/"macro_ranking_delta_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
