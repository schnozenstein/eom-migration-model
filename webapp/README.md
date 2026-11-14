# EOM Web Platform — local-first foundation

This is the first application layer around the existing EOM research repository.
It keeps the research engine and its generated outputs intact.

## Architecture in this milestone

- `backend/`: FastAPI read-only API that serves committed baseline and OECD-enhanced CSV outputs.
- `frontend/`: Next.js App Router dashboard.
- The API does not run ETL, change weights, infer missing values, or describe scores as individual migration probabilities.

## Windows setup

Requirements: Git, Python 3.11+, and Node.js 20.9+.

1. Clone the repository and switch to `feature/eom-web-platform-foundation`.
2. Start the API from the repository root:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
      py -m pip install -r webapp\backend\requirements.txt
      py -m uvicorn webapp.backend.app.main:app --reload --port 8000
   ```

3. In a second PowerShell window, start the frontend:

   ```powershell
   cd webapp\frontend
   npm install
   npm run dev
   ```

4. Open http://localhost:3000. API documentation is at http://127.0.0.1:8000/docs.

## Next milestones

1. Verify API output and add automated backend tests.
2. Add country detail and comparison views.
3. Add model-run metadata, source freshness and data lineage views.
4. Add persistence and user features only when the read-only research layer is stable.
5. Add Docker Compose and a public deployment workflow.

Use Node.js 20.9 or newer for current Next.js releases.
