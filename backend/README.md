# EOM Research API

A lightweight, read-only API that exposes the existing EOM CSV outputs. It does not change, rerun, or recalibrate the research engine.

## Requirements

- Python 3.10+
- The repository's existing `outputs/latest_macro_eom_ranking.csv`
- The repository's existing `outputs/latest_oecd_enhanced_macro_ranking.csv`

## Run on Windows PowerShell

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

If PowerShell blocks virtual-environment activation, use this for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Endpoints

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/api/v1/rankings`
- `GET http://localhost:8000/api/v1/rankings?type=oecd`
- `GET http://localhost:8000/api/v1/rankings?type=oecd&oecd_weight=10`
- `GET http://localhost:8000/api/v1/countries/SGP`
- Interactive API documentation: `http://localhost:8000/docs`

The baseline and OECD-enhanced rankings have different comparison years and country coverage. The API keeps them separate rather than silently merging unlike samples. Missing values remain null.

All scores are exploratory research indicators, not calibrated personal migration probabilities or causal estimates.
