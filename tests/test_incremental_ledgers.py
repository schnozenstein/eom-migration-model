from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from maintain_prediction_ledger import OUTCOME_COLUMNS,PREDICTION_COLUMNS,append_outcome_versions,build_prediction_outcome_join,derive_current_outcomes,revision_id,validate_prediction_ledger
from build_policy_event_delta import build_policy_delta

def outcome(target,geo,period,value,vintage="2026-01-01"):
    return {"target":target,"geography_id":geo,"geography_name":geo,"observation_period":str(period),"value":str(value),
    "unit":"net migrants per 1,000 residents","source":"WDI","source_urls_json":"{}","source_vintage":vintage,
    "recorded_at_utc":"2026-10-28T00:00:00+00:00","revision_id":revision_id(target,geo,period,value,vintage),
    "revision_type":"initial_observation","observation_definition":"test","geography_level":"country","origin":"",
    "destination":geo,"cohort":"total","quality_flag":"test","notes":""}

def test_derive_country_year_outcome_from_wdi():
    panel=pd.DataFrame([
    {"country_code":"AAA","country_code_type":"ISO3","country_name_api":"A","indicator_code":"SM.POP.NETM","year":2020,"value":1000,"api_lastupdated":"2026-01-01","source_url":"net"},
    {"country_code":"AAA","country_code_type":"ISO3","country_name_api":"A","indicator_code":"SP.POP.TOTL","year":2020,"value":100000,"api_lastupdated":"2026-01-01","source_url":"pop"},
    {"country_code":"WB_XD","country_code_type":"WB_SOURCE_ID","country_name_api":"Africa","indicator_code":"SM.POP.NETM","year":2020,"value":1000,"api_lastupdated":"2026-01-01","source_url":"net"}])
    result=derive_current_outcomes(panel,"2026-10-28T00:00:00+00:00",{"SM.POP.NETM":"net-exact","SP.POP.TOTL":"pop-exact"})
    assert len(result)==1 and abs(float(result.iloc[0]["value"])-10.0)<1e-12
    assert result.iloc[0]["geography_id"]=="AAA" and "net-exact" in result.iloc[0]["source_urls_json"]

def test_outcome_ledger_appends_only_new_keys_or_revisions():
    existing=pd.DataFrame([outcome("t","AAA",2020,1.0)],columns=OUTCOME_COLUMNS)
    current=pd.DataFrame([outcome("t","AAA",2020,1.0),outcome("t","AAA",2021,2.0),outcome("t","AAA",2020,1.5)],columns=OUTCOME_COLUMNS)
    combined,stats=append_outcome_versions(existing,current)
    assert stats=={"inserted":1,"revised":1,"unchanged":1,"stale":0}
    assert len(combined)==3 and not combined["revision_id"].duplicated().any()

def test_empty_prediction_ledger_and_forecast_outcome_join():
    assert validate_prediction_ledger(pd.DataFrame(columns=PREDICTION_COLUMNS))
    p=pd.DataFrame([{"forecast_id":"f1","issue_date":"2026-01-01","target":"t","target_period":"2025","horizon":"1","geography_id":"AAA",
    "geography_name":"AAA","model_version":"v1","point_forecast":"2.0","lower_bound":"","upper_bound":"","uncertainty_method":"",
    "assumptions":"","data_cutoff":"2024","source_vintage":"2024","calibration_status":"uncalibrated","validation_status":"exploratory",
    "issued_by_run_id":"r1","status":"issued","notes":""}],columns=PREDICTION_COLUMNS)
    joined=build_prediction_outcome_join(p,pd.DataFrame([outcome("t","AAA",2025,3.0)],columns=OUTCOME_COLUMNS))
    assert len(joined)==1 and joined.iloc[0]["join_status"]=="MATCHED" and float(joined.iloc[0]["absolute_error"])==1.0

def test_policy_hash_change_is_review_trigger_not_event():
    prev={"https://example.test/policy":{"content_sha256":"old"}}
    current=[{"country":"X","label":"official policy","url":"https://example.test/policy","final_url":"https://example.test/policy","checked_at_utc":"2026-10-28T00:00:00Z","status":"SUCCESS","http_status":"200","content_sha256":"new"}]
    rows,baseline=build_policy_delta(prev,current,"r1","success","t1")
    assert baseline and rows[0]["event_status"]=="CONTENT_CHANGED_REVIEW_REQUIRED" and rows[0]["confirmed_policy_event"]=="false"
    rows,_=build_policy_delta(prev,[dict(current[0],status="FAILED",http_status="403",content_sha256="")],"r1","success","t1")
    assert rows[0]["event_status"]=="UNKNOWN_FETCH_FAILED"
