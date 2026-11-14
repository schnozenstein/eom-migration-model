# EOM API

Read-only FastAPI service over the repository's generated ranking CSVs.

## Run locally

From the repository root, in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r webapp\backend\requirements.txt
py -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
py -m uvicorn webapp.backend.app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

The API reads `outputs/latest_macro_eom_ranking.csv` and
`outputs/latest_oecd_enhanced_macro_ranking.csv`. It does not run ETL or
recalculate scores. Missing artifacts return HTTP 503 rather than fabricated data.
