#!/usr/bin/env python3
"""Versioned ingestion of OECD International Migration Outlook 2026 statistical annex."""
from __future__ import annotations
import argparse, gzip, hashlib, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.oecd.org/en/publications/international-migration-outlook-2026_a9eab36b-en/full-report/statistical-annex_f79de055.html"
PUBLISHER = "Organisation for Economic Co-operation and Development (OECD)"
RELEASE_DATE = "2026-11-12"
TABLE_CODES = {"A.1","A.2","A.3","A.4","A.5","A.6","B.1","B.3","B.4","B.5","B.6"}
NATURAL_KEYS = ["table_code","destination","origin","measure","year"]
OUTPUT_COLUMNS = ["table_code","table_heading","destination","origin","measure","year","value","raw_value","unit","observation_status","missing_marker","publisher","source_url","release_date","source_vintage","retrieved_at_utc","run_id","raw_snapshot_sha256"]
BASE_MEASURES = {
 "A.1":("immigration_foreign_population","thousands"),
 "A.2":("emigration_foreign_population","thousands"),
 "A.3":("new_asylum_requests","persons"),
 "A.4":("foreign_born_population_stock","thousands"),
 "A.5":("foreign_population_stock","thousands"),
 "A.6":("acquisitions_of_nationality","persons"),
 "B.1":("immigration_by_nationality","thousands"),
 "B.3":("asylum_requests_by_nationality","persons"),
 "B.4":("foreign_born_stock_by_country_of_birth","thousands"),
 "B.5":("foreign_population_stock_by_nationality","thousands"),
 "B.6":("acquisitions_by_former_nationality","persons"),
}

def utc_now():
 return datetime.now(timezone.utc).isoformat()

def sha256_bytes(data: bytes) -> str:
 return hashlib.sha256(data).hexdigest()

def parse_numeric(raw: Any):
 if raw is None or (isinstance(raw,float) and pd.isna(raw)): return None,"missing",""
 text=str(raw).replace("\xa0"," ").strip()
 if text in {"","..",".","…","—","–","-"}: return None,"missing",text or "blank"
 try: return float(text.replace(" ","").replace(",","")),"observed",""
 except ValueError: return None,"unparsed",text

def flatten_columns(columns):
 out=[]
 for col in columns:
  if isinstance(col,tuple):
   parts=[str(x).strip() for x in col if str(x).strip() and not str(x).startswith("Unnamed")]
   out.append(" ".join(parts))
  else: out.append(str(col).strip())
 return out

def destination_from_heading(heading: str, table_code: str) -> str:
 if not table_code.startswith("B."): return ""
 parts=re.split(r"\s+[–—-]\s+",heading.strip())
 return parts[-1].strip() if len(parts)>1 else ""

def measure_for_row(table_code: str,label: str,previous_entity: str):
 base_measure,base_unit=BASE_MEASURES[table_code]; low=label.casefold().strip()
 if low.startswith("% of total population"):
  if table_code=="A.4": return "foreign_born_population_share","percent",previous_entity
  if table_code=="A.5": return "foreign_population_share","percent",previous_entity
 if low.startswith("% of foreign population") and table_code=="A.6":
  return "naturalisation_rate_foreign_population","percent",previous_entity
 return base_measure,base_unit,label

def extract_table(table,table_code,heading,retrieved_at,run_id,snapshot_hash):
 frames=pd.read_html(str(table),flavor="lxml")
 if not frames: return []
 frame=frames[0].copy(); frame.columns=flatten_columns(frame.columns)
 if frame.empty or len(frame.columns)<2: return []
 label_col=frame.columns[0]; year_columns=[]; female_columns=[]
 for col in frame.columns[1:]:
  match=re.search(r"\b(19\d{2}|20\d{2})\b",str(col))
  if not match: continue
  year=int(match.group(1))
  if "women" in str(col).casefold() or "female" in str(col).casefold(): female_columns.append((col,year))
  else: year_columns.append((col,year))
 if not year_columns: return []
 destination=destination_from_heading(heading,table_code); rows=[]; previous_entity=""
 for _,row in frame.iterrows():
  label=str(row[label_col]).strip()
  if not label or label.casefold() in {"nan","none"}: continue
  measure,unit,entity=measure_for_row(table_code,label,previous_entity)
  if measure==BASE_MEASURES[table_code][0]: entity=label; previous_entity=label
  if table_code.startswith("B."): origin=entity; dest=destination
  else: origin=""; dest=entity
  for col,year in year_columns:
   raw=row[col]; value,status,marker=parse_numeric(raw)
   rows.append({"table_code":table_code,"table_heading":heading,"destination":dest,"origin":origin,"measure":measure,"year":year,"value":value,"raw_value":"" if raw is None else str(raw).strip(),"unit":unit,"observation_status":status,"missing_marker":marker,"publisher":PUBLISHER,"source_url":SOURCE_URL,"release_date":RELEASE_DATE,"source_vintage":f"IMO2026-{RELEASE_DATE}","retrieved_at_utc":retrieved_at,"run_id":run_id,"raw_snapshot_sha256":snapshot_hash})
  for col,year in female_columns:
   raw=row[col]; value,status,marker=parse_numeric(raw)
   rows.append({"table_code":table_code,"table_heading":heading,"destination":dest,"origin":origin,"measure":"female_share_of_origin_stock","year":year,"value":value,"raw_value":"" if raw is None else str(raw).strip(),"unit":"percent","observation_status":status,"missing_marker":marker,"publisher":PUBLISHER,"source_url":SOURCE_URL,"release_date":RELEASE_DATE,"source_vintage":f"IMO2026-{RELEASE_DATE}","retrieved_at_utc":retrieved_at,"run_id":run_id,"raw_snapshot_sha256":snapshot_hash})
 return rows

def parse_annex_html(html,retrieved_at,run_id,snapshot_hash):
 soup=BeautifulSoup(html,"html.parser"); rows=[]; table_counts=Counter()
 for heading_node in soup.find_all(re.compile(r"^h[1-6]$")):
  heading=" ".join(heading_node.get_text(" ",strip=True).split())
  match=re.search(r"\bTable\s+([AB]\.\d+)\b",heading,flags=re.I)
  if not match: continue
  code=match.group(1).upper()
  if code not in TABLE_CODES: continue
  table=heading_node.find_next("table")
  if table is None: continue
  extracted=extract_table(table,code,heading,retrieved_at,run_id,snapshot_hash)
  if extracted: rows.extend(extracted); table_counts[code]+=len(extracted)
 frame=pd.DataFrame(rows,columns=OUTPUT_COLUMNS)
 if frame.empty: raise ValueError("No OECD annex tables were parsed from the official HTML page.")
 frame["year"]=pd.to_numeric(frame["year"],errors="raise").astype(int); frame["value"]=pd.to_numeric(frame["value"],errors="coerce")
 duplicates=int(frame.duplicated(NATURAL_KEYS).sum())
 if duplicates:
  conflicts=frame.groupby(NATURAL_KEYS,dropna=False)["raw_value"].nunique()
  if len(conflicts[conflicts>1]): raise ValueError("Conflicting duplicate OECD annex natural keys")
  frame=frame.drop_duplicates(NATURAL_KEYS,keep="first")
 required={"A.1","A.4","B.4","A.6"}; missing=sorted(required-set(table_counts))
 if missing: raise ValueError(f"Required OECD tables not found or parsed: {missing}")
 audit={"table_observation_rows":dict(sorted(table_counts.items())),"tables_parsed":sorted(table_counts),"required_tables_missing":missing,"natural_key_columns":NATURAL_KEYS,"duplicate_natural_keys_rejected":duplicates,"observation_start":int(frame.year.min()),"observation_end":int(frame.year.max()),"destinations":sorted(x for x in frame.destination.dropna().unique() if x),"origins":sorted(x for x in frame.origin.dropna().unique() if x),"missing_observations":int(frame.value.isna().sum()),"unparsed_observations":int((frame.observation_status=="unparsed").sum())}
 return frame.sort_values(NATURAL_KEYS,kind="stable").reset_index(drop=True),audit

def append_revision_history(current,history_path):
 history_path.parent.mkdir(parents=True,exist_ok=True)
 old=pd.read_csv(history_path,dtype={"raw_value":"string"}) if history_path.exists() else pd.DataFrame(columns=OUTPUT_COLUMNS)
 if old.empty: latest=old
 else:
  old["retrieved_at_utc"]=pd.to_datetime(old["retrieved_at_utc"],errors="coerce",utc=True)
  latest=old.sort_values("retrieved_at_utc",kind="stable").drop_duplicates(NATURAL_KEYS,keep="last")
 old_index={tuple(row[k] if pd.notna(row[k]) else "" for k in NATURAL_KEYS):row for _,row in latest.iterrows()}
 additions=[]; inserted=revised=unchanged=0
 for _,row in current.iterrows():
  key=tuple(row[k] if pd.notna(row[k]) else "" for k in NATURAL_KEYS); prior=old_index.get(key)
  if prior is None: additions.append(row.to_dict()); inserted+=1; continue
  ov=None if pd.isna(prior.get("value")) else float(prior.get("value")); nv=None if pd.isna(row.get("value")) else float(row.get("value"))
  same=ov==nv and str(prior.get("raw_value",""))==str(row.get("raw_value","")) and str(prior.get("observation_status",""))==str(row.get("observation_status",""))
  if same: unchanged+=1
  else: additions.append(row.to_dict()); revised+=1
 if additions:
  history=pd.concat([old,pd.DataFrame(additions)],ignore_index=True); history.to_csv(history_path,index=False)
 else:
  history=old
  if not history_path.exists(): history.to_csv(history_path,index=False)
 return {"inserted_new_natural_keys":inserted,"appended_value_revisions":revised,"unchanged_keys_skipped":unchanged,"history_rows_after":int(len(history)),"history_unique_natural_keys":int(history[NATURAL_KEYS].drop_duplicates().shape[0]) if not history.empty else 0}

def run(url=SOURCE_URL,release_date=RELEASE_DATE,run_id=None):
 run_id=run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); retrieved_at=utc_now()
 response=requests.get(url,timeout=(15,90),headers={"User-Agent":"EOM-Research-ETL/1.0 (reproducible academic research)"})
 response.raise_for_status(); response.encoding=response.encoding or "utf-8"; raw=response.content; digest=sha256_bytes(raw)
 snap=ROOT/"data"/"raw"/"snapshots"/"oecd_imo_2026"/run_id; snap.mkdir(parents=True,exist_ok=True)
 raw_path=snap/"statistical_annex.html.gz"
 with gzip.open(raw_path,"wb") as stream: stream.write(raw)
 frame,audit=parse_annex_html(response.text,retrieved_at,run_id,digest)
 frame["release_date"]=release_date; frame["source_vintage"]=f"IMO2026-{release_date}"
 curdir=ROOT/"data"/"derived"/"oecd_imo_2026"; curdir.mkdir(parents=True,exist_ok=True)
 current_path=curdir/f"annex_long_{run_id}.csv"; frame.to_csv(current_path,index=False)
 history_path=ROOT/"data"/"observations_history"/"oecd_imo_2026_annex_history.csv"
 history_stats=append_revision_history(frame,history_path)
 manifest={"run_id":run_id,"publisher":PUBLISHER,"release_date":release_date,"retrieved_at_utc":retrieved_at,"source_url":url,"source_status":"SUCCESS","http_status":response.status_code,"raw_snapshot_path":str(raw_path.relative_to(ROOT)),"raw_snapshot_sha256":digest,"raw_snapshot_bytes":len(raw),"current_extract_path":str(current_path.relative_to(ROOT)),"history_path":str(history_path.relative_to(ROOT)),"definitions":{k:v[0] for k,v in BASE_MEASURES.items()},"unit_note":"Table-specific units are preserved; stock, flow, asylum and naturalisation measures are not combined.","comparability_warning":"OECD notes national definitions differ and annex series are not fully comparable across countries.","observation_period":[int(frame.year.min()),int(frame.year.max())],**audit,**history_stats}
 md=ROOT/"metadata"/"oecd_imo_2026"; md.mkdir(parents=True,exist_ok=True)
 manifest_path=md/f"annex_manifest_{run_id}.json"; status_path=md/f"annex_source_status_{run_id}.csv"
 report_path=ROOT/"reports"/f"oecd_imo_2026_annex_{run_id}.md"; report_path.parent.mkdir(parents=True,exist_ok=True)
 pd.DataFrame([{"source_id":"OECD_IMO_2026_STATISTICAL_ANNEX","publisher":PUBLISHER,"source_url":url,"release_date":release_date,"retrieved_at_utc":retrieved_at,"observation_start":audit["observation_start"],"observation_end":audit["observation_end"],"status":"SUCCESS","rows_parsed":len(frame),"tables_parsed":";".join(audit["tables_parsed"]),"raw_snapshot_sha256":digest,"error":""}]).to_csv(status_path,index=False)
 report=f"# OECD International Migration Outlook 2026 — Annex ingestion\n\n- Run: {run_id}\n- Release date: {release_date}\n- Retrieved: {retrieved_at}\n- Source: {url}\n- Parsed observations: {len(frame):,}\n- Missing cells preserved: {audit['missing_observations']:,}\n- Tables parsed: {', '.join(audit['tables_parsed'])}\n- New keys: {history_stats['inserted_new_natural_keys']:,}\n- Revisions appended: {history_stats['appended_value_revisions']:,}\n- Unchanged keys skipped: {history_stats['unchanged_keys_skipped']:,}\n\n## Safeguards\n\n- A-series destination totals and B-series origin/nationality breakdowns remain separate.\n- Asylum, population stocks, migration flows and nationality acquisitions are distinct outcomes.\n- Missing markers are preserved, not converted to zero.\n- OECD national definitions differ; no cross-country harmonisation is assumed.\n- These data do not automatically feed the EOM ranking or calibrate EOM.\n"
 report_path.write_text(report,encoding="utf-8")
 manifest.update({"manifest_path":str(manifest_path.relative_to(ROOT)),"status_path":str(status_path.relative_to(ROOT)),"report_path":str(report_path.relative_to(ROOT))})
 manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
 return manifest

def main():
 parser=argparse.ArgumentParser(); parser.add_argument("--url",default=SOURCE_URL); parser.add_argument("--release-date",default=RELEASE_DATE); parser.add_argument("--run-id",default=None)
 args=parser.parse_args(); print(json.dumps(run(args.url,args.release_date,args.run_id),indent=2,ensure_ascii=False))
if __name__=="__main__": main()
