#!/usr/bin/env python3
"""Offline audit of the general EOM processed panels; performs no fitting or imputation."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OUT=DATA/'data_quality_audit_general_rerun.csv'
panel=pd.read_csv(DATA/'historical_destination_year_panel.csv')
rows=[]
for c in panel.columns:
    if c in {'destination','year','data_level_note'} or c.startswith('missing_'): continue
    m=panel[c].notna(); n=int(m.sum())
    rows.append({'dataset':'historical_destination_year_panel.csv','indicator':c,'expected_cells':len(panel),'observed_cells':n,'missing_cells':len(panel)-n,'coverage_pct':round(100*n/len(panel),2),'geographies_with_value':int(panel.loc[m,'destination'].nunique()),'year_min':int(panel.loc[m,'year'].min()) if n else None,'year_max':int(panel.loc[m,'year'].max()) if n else None})
for fname in ['eurostat_selected_total_indicators_long.csv','eurostat_new_migration_indicators_long.csv']:
    df=pd.read_csv(DATA/fname)
    for name,g in df.groupby('indicator'):
        n=int(g['value'].notna().sum()); total=len(g)
        rows.append({'dataset':fname,'indicator':name,'expected_cells':total,'observed_cells':n,'missing_cells':total-n,'coverage_pct':round(100*n/total,2),'geographies_with_value':int(g.loc[g.value.notna(),'destination'].nunique()),'year_min':int(g.loc[g.value.notna(),'year'].min()) if n else None,'year_max':int(g.loc[g.value.notna(),'year'].max()) if n else None})
pd.DataFrame(rows).to_csv(OUT,index=False)
print(f'Wrote {len(rows)} audit rows to {OUT}')
print('This script audits coverage only; it does not fit, forecast, calibrate, rank, or estimate causal effects.')
