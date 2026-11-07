"""Incremental bilateral migration-flow ingestion and gravity/EOM benchmark."""
from __future__ import annotations
import gzip, hashlib, io, json, math, warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pycountry
import requests

ROOT = Path(__file__).resolve().parents[2]
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
CEPII_URL = "https://www.cepii.fr/DATA_DOWNLOAD/gravity/dist_cepii.xls"
MAIN_DATASET, CHECK_DATASET = "migr_imm5prv", "migr_emi3nxt"
HISTORY = ROOT / "data/bilateral/eurostat_od_flows_history.csv.gz"
WDI = ROOT / "data/raw/world_bank_long.csv"
SPECIAL_ISO2 = {"EL": "GRC", "UK": "GBR", "XK": "XKX"}
KEYS = ["dataset", "measure", "origin_iso3", "destination_iso3", "year"]
HISTORY_COLS = KEYS + ["flow_persons", "observation_status", "source_flag", "unit",
    "source_url", "publisher", "retrieved_at_utc", "revision_number",
    "revision_type", "previous_value", "record_hash"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def iso2_to_iso3(value: Any) -> str | None:
    code = str(value or "").strip().upper()
    if code in SPECIAL_ISO2:
        return SPECIAL_ISO2[code]
    try:
        found = pycountry.countries.get(alpha_2=code)
        return found.alpha_3 if found else None
    except (LookupError, AttributeError):
        return None


def _codes(dimension):
    index = dimension.get("category", {}).get("index", {})
    if isinstance(index, list):
        return [str(v) for v in index]
    if isinstance(index, dict):
        return [k for k, _ in sorted(index.items(), key=lambda item: item[1])]
    raise ValueError("JSON-stat dimension missing category index")


def parse_jsonstat(payload: dict, dataset: str) -> pd.DataFrame:
    ids, sizes, dims = payload.get("id"), payload.get("size"), payload.get("dimension")
    if not isinstance(ids, list) or not isinstance(sizes, list) or not isinstance(dims, dict) or len(ids) != len(sizes):
        raise ValueError(f"{dataset}: invalid JSON-stat structure")
    categories = [_codes(dims[d]) for d in ids]
    if any(len(c) != int(n) for c, n in zip(categories, sizes)):
        raise ValueError(f"{dataset}: dimension size mismatch")
    values, statuses = payload.get("value", {}), payload.get("status", {})
    items = values.items() if isinstance(values, dict) else enumerate(values)
    total = int(np.prod(sizes))
    strides = [int(np.prod(sizes[i + 1:])) for i in range(len(sizes))]
    rows = []
    for index, value in items:
        index = int(index)
        if index < 0 or index >= total:
            raise ValueError(f"{dataset}: invalid flat index")
        coords = [(index // stride) % int(size) for stride, size in zip(strides, sizes)]
        row = {dim: categories[i][coords[i]] for i, dim in enumerate(ids)}
        if isinstance(statuses, dict):
            flag = statuses.get(str(index), "")
        elif isinstance(statuses, list) and index < len(statuses):
            flag = statuses[index]
        else:
            flag = ""
        row.update({"value": value, "observation_status": str(flag or ""), "flat_index": index})
        rows.append(row)
    return pd.DataFrame(rows)


def orient_rows(raw: pd.DataFrame, dataset: str, url: str, retrieved: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    required = {"geo", "partner", "time", "value"}
    if required - set(raw.columns):
        raise ValueError(f"{dataset}: required dimensions absent: {sorted(required-set(raw.columns))}")
    out = []
    for row in raw.to_dict("records"):
        try:
            value = float(row["value"])
            year = int(str(row["time"])[:4])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value < 0:
            continue
        geo, partner = iso2_to_iso3(row["geo"]), iso2_to_iso3(row["partner"])
        if not geo or not partner or geo == partner:
            continue
        if dataset == MAIN_DATASET:
            origin, destination, measure = partner, geo, "immigration_previous_residence"
        elif dataset == CHECK_DATASET:
            origin, destination, measure = geo, partner, "emigration_next_residence"
        else:
            raise ValueError(f"Unexpected dataset {dataset}")
        out.append({
            "dataset": dataset, "measure": measure,
            "origin_iso3": origin, "destination_iso3": destination, "year": year,
            "flow_persons": value, "observation_status": row.get("observation_status", ""),
            "source_flag": row.get("flag", row.get("obs_status", "")), "unit": "NR",
            "source_url": url, "publisher": "Eurostat", "retrieved_at_utc": retrieved
        })
    return pd.DataFrame(out)


def fetch_eurostat(dataset: str, start: int, end: int, snapshot_dir: Path):
    params = {"lang":"en", "freq":"A", "unit":"NR", "agedef":"REACH",
              "age":"TOTAL", "sex":"T", "sinceTimePeriod":str(start), "untilTimePeriod":str(end)}
    url = f"{EUROSTAT_BASE}/{dataset}"
    retrieved = utc_now()
    response = requests.get(url, params=params, timeout=(20,180),
                            headers={"User-Agent":"EOM-Research/1.0"})
    response.raise_for_status()
    payload = response.json()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    raw_path = snapshot_dir / f"{dataset}.json.gz"
    with gzip.open(raw_path, "wt", encoding="utf-8") as stream:
        json.dump(payload, stream, separators=(",",":"))
    parsed = parse_jsonstat(payload, dataset)
    status = {"dataset":dataset, "publisher":"Eurostat", "url":url,
              "resolved_url":response.url, "query_params":params,
              "retrieved_at_utc":retrieved, "status":"SUCCESS",
              "http_status":response.status_code, "numeric_cells":int(parsed["value"].notna().sum()),
              "status_flagged_cells":int(parsed["observation_status"].ne("").sum()),
              "raw_snapshot":str(raw_path.relative_to(ROOT)), "raw_size_bytes":raw_path.stat().st_size}
    return parsed, status


def fetch_geodist(snapshot_dir: Path):
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / "dist_cepii.xls"
    response = requests.get(CEPII_URL, timeout=(20,180),
                            headers={"User-Agent":"EOM-Research/1.0"})
    response.raise_for_status()
    path.write_bytes(response.content)
    frame = pd.read_excel(io.BytesIO(response.content), engine="xlrd")
    required = {"iso_o","iso_d"}
    if not required.issubset(frame.columns):
        raise ValueError(f"CEPII missing columns {sorted(required-set(frame.columns))}")
    distance = "distw" if "distw" in frame.columns else "dist"
    if distance not in frame.columns:
        raise ValueError("CEPII distance field unavailable")
    for col in ["contig","comlang_off"]:
        if col not in frame:
            frame[col] = np.nan
    frame = frame.rename(columns={distance:"distance_km"})
    frame["iso_o"] = frame["iso_o"].astype(str).str.upper()
    frame["iso_d"] = frame["iso_d"].astype(str).str.upper()
    frame = frame.drop_duplicates(["iso_o","iso_d"])
    audit = {"publisher":"CEPII", "url":CEPII_URL, "retrieved_at_utc":utc_now(),
             "status":"SUCCESS", "rows":int(len(frame)), "distance_field":distance,
             "raw_snapshot":str(path.relative_to(ROOT)), "raw_size_bytes":path.stat().st_size,
             "license":"Etalab Open License 2.0 per CEPII download page"}
    return frame[["iso_o","iso_d","distance_km","contig","comlang_off"]], audit


def _hash_record(row):
    raw = "|".join([str(row.get(k,"")) for k in KEYS] +
        [format(float(row["flow_persons"]),".12g"),str(row.get("observation_status","")),str(row.get("source_flag",""))])
    return hashlib.sha256(raw.encode()).hexdigest()


def append_history(rows: pd.DataFrame, path: Path = HISTORY):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(path, compression="gzip") if path.exists() else pd.DataFrame(columns=HISTORY_COLS)
    if rows.empty:
        if not path.exists():
            old.to_csv(path,index=False,compression="gzip")
        return {"inserted":0,"revised":0,"unchanged":0,"duplicates_in_run":0,"history_rows":len(old)}
    new = rows.copy()
    new["record_hash"] = new.apply(_hash_record,axis=1)
    duplicates = int(new.duplicated(KEYS,keep="last").sum())
    new = new.drop_duplicates(KEYS,keep="last")
    latest = {}
    if not old.empty:
        old = old.sort_values(["retrieved_at_utc","revision_number"])
        for _, row in old.iterrows():
            latest[tuple(row[k] for k in KEYS)] = row
    append, inserted, revised, unchanged = [],0,0,0
    for _, row in new.iterrows():
        key = tuple(row[k] for k in KEYS)
        prev = latest.get(key)
        if prev is None:
            rev, kind, prev_value = 1,"initial",np.nan
            inserted += 1
        elif prev.get("record_hash") == row["record_hash"]:
            unchanged += 1
            continue
        else:
            rev, kind, prev_value = int(prev.get("revision_number",1))+1,"source_revision",prev.get("flow_persons")
            revised += 1
        record = row.to_dict()
        record.update({"revision_number":rev,"revision_type":kind,"previous_value":prev_value})
        append.append(record)
        latest[key] = pd.Series(record)
    if append:
        old = pd.concat([old,pd.DataFrame(append)],ignore_index=True)
    for col in HISTORY_COLS:
        if col not in old:
            old[col] = np.nan
    old[HISTORY_COLS].to_csv(path,index=False,compression="gzip")
    return {"inserted":inserted,"revised":revised,"unchanged":unchanged,
            "duplicates_in_run":duplicates,"history_rows":len(old)}


def load_wdi_features(path: Path = WDI) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing refreshed WDI extract: {path}")
    from .model import to_wide, add_derived_features, equal_weight_energy
    long = pd.read_csv(path, low_memory=False)
    if "country_region_id" in long:
        long = long[long["country_region_id"].notna()].copy()
    wide = add_derived_features(to_wide(long))
    energies = []
    for year, group in wide.groupby("year"):
        score = equal_weight_energy(group)
        energies.append(score[["country_code","year","energy_equal_weight"]])
    energy = pd.concat(energies,ignore_index=True) if energies else pd.DataFrame()
    for col in ["NY.GDP.PCAP.PP.KD","SP.POP.TOTL"]:
        if col not in wide:
            wide[col] = np.nan
    result = wide[["country_code","year","NY.GDP.PCAP.PP.KD","SP.POP.TOTL"]].merge(
        energy,on=["country_code","year"],how="left")
    result = result.rename(columns={"country_code":"country_iso3",
        "NY.GDP.PCAP.PP.KD":"gdp_pc_ppp","SP.POP.TOTL":"population",
        "energy_equal_weight":"eom_energy"})
    for col in ["gdp_pc_ppp","population","eom_energy"]:
        result[col] = pd.to_numeric(result[col],errors="coerce")
    return result.replace([np.inf,-np.inf],np.nan)


def prepare_panel(flows: pd.DataFrame, geodist: pd.DataFrame, features: pd.DataFrame):
    primary = flows[flows["measure"]=="immigration_previous_residence"].copy()
    primary["feature_year"] = primary["year"] - 1
    origin = features.rename(columns={"country_iso3":"origin_iso3","year":"feature_year",
        "gdp_pc_ppp":"gdp_pc_origin","population":"population_origin","eom_energy":"eom_energy_origin"})
    destination = features.rename(columns={"country_iso3":"destination_iso3","year":"feature_year",
        "gdp_pc_ppp":"gdp_pc_destination","population":"population_destination","eom_energy":"eom_energy_destination"})
    panel = primary.merge(origin,on=["origin_iso3","feature_year"],how="left")
    panel = panel.merge(destination,on=["destination_iso3","feature_year"],how="left")
    panel = panel.merge(geodist,left_on=["origin_iso3","destination_iso3"],
        right_on=["iso_o","iso_d"],how="left")
    panel["eom_attractor_gap"] = panel["eom_energy_origin"] - panel["eom_energy_destination"]
    distance = pd.to_numeric(panel["distance_km"],errors="coerce")
    panel["log_distance"] = np.log(distance.where(distance>0))
    for col in ["population_origin","population_destination","gdp_pc_origin","gdp_pc_destination"]:
        vals = pd.to_numeric(panel[col],errors="coerce")
        panel["log_"+col] = np.log(vals.where(vals>0))
    panel["year_centered"] = panel["year"] - panel["year"].min()
    return panel


def metrics(frame: pd.DataFrame, prediction: str):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_poisson_deviance
    from scipy.stats import spearmanr
    values = frame[["flow_persons",prediction]].replace([np.inf,-np.inf],np.nan).dropna()
    if values.empty:
        return {"n":0,"mae":None,"rmse":None,"poisson_deviance":None,"spearman":None}
    y = values.flow_persons.to_numpy(float)
    p = np.maximum(values[prediction].to_numpy(float),1e-9)
    rho = spearmanr(y,p).statistic if len(y)>2 and np.unique(y).size>1 and np.unique(p).size>1 else np.nan
    return {"n":len(y),"mae":float(mean_absolute_error(y,p)),
        "rmse":float(np.sqrt(mean_squared_error(y,p))),
        "poisson_deviance":float(mean_poisson_deviance(y,p)) if np.all(y>=0) else None,
        "spearman":float(rho) if np.isfinite(rho) else None}


def cluster_bootstrap_difference(pred: pd.DataFrame, repeats=300, seed=20261107):
    data = pred.dropna(subset=["flow_persons","gravity_prediction","gravity_eom_prediction"]).copy()
    if data.empty:
        return {"clusters":0,"ci95":[None,None]}
    data["pair_id"] = data.origin_iso3.astype(str)+"->"+data.destination_iso3.astype(str)
    groups = {k:v for k,v in data.groupby("pair_id")}
    keys = np.array(list(groups),dtype=object)
    if len(keys)<2:
        return {"clusters":len(keys),"ci95":[None,None]}
    rng=np.random.default_rng(seed); diffs=[]
    for _ in range(repeats):
        sample=rng.choice(keys,size=len(keys),replace=True)
        draw=pd.concat([groups[k] for k in sample],ignore_index=True)
        diffs.append(float(np.mean(np.abs(draw.flow_persons-draw.gravity_prediction))-
            np.mean(np.abs(draw.flow_persons-draw.gravity_eom_prediction))))
    return {"clusters":len(keys),"repetitions":repeats,"mean_mae_difference":float(np.mean(diffs)),
        "ci95":[float(np.quantile(diffs,.025)),float(np.quantile(diffs,.975))],
        "positive_favours_eom":True}


def evaluate(panel: pd.DataFrame):
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    needed=["flow_persons","origin_iso3","destination_iso3","year","log_population_origin",
        "log_population_destination","log_gdp_pc_origin","log_gdp_pc_destination",
        "log_distance","contig","comlang_off","eom_attractor_gap"]
    missing=set(needed)-set(panel.columns)
    if missing:
        raise ValueError(f"Missing benchmark variables: {sorted(missing)}")
    data=panel.replace([np.inf,-np.inf],np.nan).dropna(subset=needed).copy()
    data["flow_persons"]=pd.to_numeric(data.flow_persons,errors="coerce")
    data["contig"]=pd.to_numeric(data.contig,errors="coerce")
    data["comlang_off"]=pd.to_numeric(data.comlang_off,errors="coerce")
    data=data.dropna(subset=["flow_persons","contig","comlang_off"])
    data=data[data.flow_persons>=0]
    duplicates=int(data.duplicated(["origin_iso3","destination_iso3","year"]).sum())
    data=data.drop_duplicates(["origin_iso3","destination_iso3","year"])
    if data.empty:
        return {"status":"insufficient_data","complete_case_rows":0,"duplicate_rows":duplicates},pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    base=("flow_persons ~ log_population_origin + log_population_destination + "
        "log_gdp_pc_origin + log_gdp_pc_destination + log_distance + contig + comlang_off + "
        "year_centered + C(origin_iso3) + C(destination_iso3)")
    augmented=base+" + eom_attractor_gap"
    years=sorted(data.year.astype(int).unique())
    predictions=[]; folds=[]; coefs=[]
    min_train=max(150,int(len(data)*.10))
    for year in years:
        train=data[data.year<year].copy()
        test=data[data.year==year].copy()
        if len(train)<min_train or len(test)<25: continue
        origins=set(train.origin_iso3); destinations=set(train.destination_iso3)
        test=test[test.origin_iso3.isin(origins)&test.destination_iso3.isin(destinations)]
        if len(test)<25: continue
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                m0=smf.glm(base,data=train,family=sm.families.Poisson()).fit(maxiter=200)
                m1=smf.glm(augmented,data=train,family=sm.families.Poisson()).fit(maxiter=200)
            out=test[["origin_iso3","destination_iso3","year","flow_persons","eom_attractor_gap"]].copy()
            out["gravity_prediction"]=np.maximum(np.asarray(m0.predict(test)),1e-9)
            out["gravity_eom_prediction"]=np.maximum(np.asarray(m1.predict(test)),1e-9)
            prior=data[["origin_iso3","destination_iso3","year","flow_persons"]].copy()
            prior["year"]=prior.year+1
            prior=prior.rename(columns={"flow_persons":"persistence_prediction"})
            out=out.merge(prior,on=["origin_iso3","destination_iso3","year"],how="left")
            predictions.append(out)
            folds.append({"target_year":int(year),"train_rows":len(train),"test_rows":len(test),
                "test_rows_with_persistence":int(out.persistence_prediction.notna().sum()),
                "train_origins":int(train.origin_iso3.nunique()),"train_destinations":int(train.destination_iso3.nunique()),
                "baseline_converged":bool(m0.converged),"eom_converged":bool(m1.converged),
                "warnings":" | ".join(str(w.message) for w in caught[:3]),"status":"scored"})
            for label,model in [("gravity_ppml",m0),("gravity_plus_eom_ppml",m1)]:
                for term,value in model.params.items():
                    coefs.append({"fold_year":int(year),"model":label,"term":term,
                        "coefficient":float(value),"standard_error":float(model.bse.get(term,np.nan)),
                        "p_value":float(model.pvalues.get(term,np.nan)),"converged":bool(model.converged)})
        except Exception as exc:
            folds.append({"target_year":int(year),"train_rows":len(train),"test_rows":len(test),
                "status":"fit_failed","error":f"{type(exc).__name__}: {exc}"})
    pred=pd.concat(predictions,ignore_index=True) if predictions else pd.DataFrame()
    fold_df=pd.DataFrame(folds); coef_df=pd.DataFrame(coefs)
    if pred.empty:
        summary={"status":"insufficient_data_or_fit_failure","complete_case_rows":len(data),
            "origins":int(data.origin_iso3.nunique()),"destinations":int(data.destination_iso3.nunique()),
            "available_years":years,"folds_attempted":len(fold_df),"folds_scored":0,
            "duplicate_pair_year_rows_removed":duplicates}
    else:
        persistence=pred.dropna(subset=["persistence_prediction"])
        summary={"status":"completed_expanding_origin_bilateral_benchmark",
            "target":"annual persons immigrating to reporting destination whose previous usual residence was origin country",
            "primary_source":MAIN_DATASET,
            "flow_direction":"origin=partner previous usual residence; destination=reporting geo",
            "feature_timing":"GDP, population and EOM features from t-1; migration flow from t",
            "benchmark":"Poisson pseudo-maximum-likelihood GLM with origin and destination fixed effects",
            "EOM_comparison":"same PPML gravity specification plus equal-weight EOM energy-origin minus energy-destination gap",
            "EOM_gap_interpretation":"positive means destination EOM energy is lower; stronger attractor under paper sign convention",
            "same_complete_case_test_sample":True,
            "gravity_ppml":metrics(pred,"gravity_prediction"),
            "gravity_plus_eom_ppml":metrics(pred,"gravity_eom_prediction"),
            "pair_persistence":metrics(persistence,"persistence_prediction"),
            "EOM_minus_gravity_MAE_cluster_bootstrap":cluster_bootstrap_difference(pred),
            "complete_case_rows":len(data),"origins":int(data.origin_iso3.nunique()),
            "destinations":int(data.destination_iso3.nunique()),
            "years":[int(data.year.min()),int(data.year.max())],"rows_scored":len(pred),
            "scored_years":sorted(int(y) for y in pred.year.unique()),
            "folds_attempted":len(fold_df),"folds_scored":int((fold_df.status=="scored").sum()),
            "duplicate_pair_year_rows_removed":duplicates,
            "sample_selection":"Only observed numeric, non-suppressed pair-year cells with complete t-1 WDI and CEPII features; missing/suppressed values are not zero-imputed.",
            "persistence_sample":"Only scored pairs with an actual observed t-1 flow; absent prior pair-years are not assigned zero.",
            "interpretation_guardrail":"Predictive comparison, not causal. Current equal-weight EOM macro proxy overlaps GDP/labour/institutional gravity covariates; incremental association does not validate the full EOM theory."}
    return summary,pred,fold_df,coef_df


def run(start_year=2010,end_year=2024):
    stamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    dated=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    euro_dir=ROOT/"data/raw/snapshots/eurostat_bilateral"/dated
    ce_dir=ROOT/"data/raw/snapshots/cepii_geodist"/dated
    audit={"run_id":stamp,"retrieved_at_utc":utc_now(),"start_year":start_year,"end_year":end_year,
        "sources":[],"numeric_rows_fetched":0,"status":"started"}
    tables=[]; failures=[]
    for dataset in [MAIN_DATASET,CHECK_DATASET]:
        try:
            raw,status=fetch_eurostat(dataset,start_year,end_year,euro_dir)
            audit["sources"].append(status)
            audit["numeric_rows_fetched"]+=int(raw.value.notna().sum()) if not raw.empty else 0
            oriented=orient_rows(raw,dataset,status["resolved_url"],status["retrieved_at_utc"])
            status["normalized_country_pair_rows"]=len(oriented)
            status["unmapped_or_aggregate_rows"]=max(0,len(raw)-len(oriented))
            tables.append(oriented)
        except Exception as exc:
            failures.append({"source":dataset,"url":f"{EUROSTAT_BASE}/{dataset}",
                "status":"FAILED","error":f"{type(exc).__name__}: {exc}"})
    if not tables or tables[0].empty:
        audit["sources"].extend(failures); audit["status"]="blocked_no_primary_bilateral_flow"
        (ROOT/"metadata").mkdir(parents=True,exist_ok=True)
        (ROOT/"metadata/bilateral_gravity_data_audit.json").write_text(json.dumps(audit,indent=2))
        raise RuntimeError("No primary Eurostat bilateral immigration flows retrieved.")
    all_flows=pd.concat(tables,ignore_index=True)
    history=append_history(all_flows)
    audit.update({"rows_inserted":history["inserted"],"rows_revised":history["revised"],
        "rows_unchanged":history["unchanged"],"duplicates_in_run":history["duplicates_in_run"],
        "history_rows":history["history_rows"]})
    geodist,ce_audit=fetch_geodist(ce_dir); audit["sources"].append(ce_audit)
    features=load_wdi_features()
    panel=prepare_panel(all_flows,geodist,features)
    summary,pred,folds,coef=evaluate(panel)
    summary.update({"retrieval_run_id":stamp,"data_cutoff_utc":utc_now(),
        "source_failures":failures,"reverse_flow_crosscheck_rows":int((all_flows.measure=="emigration_next_residence").sum())})
    audit["benchmark"]={"status":summary["status"],"panel_rows_after_join":len(panel),
        "complete_case_rows":summary.get("complete_case_rows",0),
        "rows_scored":summary.get("rows_scored",0),"folds_scored":summary.get("folds_scored",0)}
    audit["sources"].extend(failures); audit["status"]="completed"
    for folder in ["outputs","metadata","reports","data/bilateral"]:
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    (ROOT/"outputs/bilateral_gravity_benchmark.json").write_text(json.dumps(summary,indent=2,default=str)+"\n")
    pred.to_csv(ROOT/"outputs/bilateral_gravity_benchmark_predictions.csv",index=False)
    folds.to_csv(ROOT/"outputs/bilateral_gravity_benchmark_folds.csv",index=False)
    coef.to_csv(ROOT/"outputs/bilateral_gravity_model_coefficients.csv",index=False)
    (ROOT/"metadata/bilateral_gravity_data_audit.json").write_text(json.dumps(audit,indent=2,default=str)+"\n")
    report=["# Bilateral gravity benchmark", "",f"Run: {stamp}",f"Status: {summary['status']}",
        f"Complete-case OD-year rows: {summary.get('complete_case_rows',0):,}",
        f"Scored predictions: {summary.get('rows_scored',0):,}",
        f"Origins/destinations: {summary.get('origins',0)} / {summary.get('destinations',0)}",
        f"Scored folds: {summary.get('folds_scored',0)}","","Model metrics:",
        json.dumps({k:summary[k] for k in ["gravity_ppml","gravity_plus_eom_ppml","pair_persistence","EOM_minus_gravity_MAE_cluster_bootstrap"] if k in summary},indent=2),"",
        "Only observed numeric pair-year cells with complete lagged features and CEPII covariates are scored. Missing/suppressed pairs are not imputed as zero. This is a predictive test, not a causal estimate.","",
        "Source failures:",json.dumps(failures,indent=2)]
    (ROOT/"reports/bilateral_gravity_benchmark_latest.md").write_text("\n".join(report)+"\n")
    return {"summary":summary,"audit":audit}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--start-year",type=int,default=2010)
    parser.add_argument("--end-year",type=int,default=2024)
    args=parser.parse_args()
    print(json.dumps(run(args.start_year,args.end_year),indent=2,default=str))
