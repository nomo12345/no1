# no1

## Setup ✅

1. Create a virtual environment (recommended):

   python -m venv .venv
   source .venv/bin/activate

2. Install dependencies:

   pip install -r requirements.txt

3. Run the app:

   python papa.py

The application listens on http://127.0.0.1:8080 by default.

Deploying to Render (quick):

1. Ensure `requirements.txt` includes `gunicorn` (already added).
2. Add your repo to Render and create a **Web Service**.
   - Build command: (leave default)
   - Start command: `gunicorn papa:app --bind 0.0.0.0:$PORT --workers 2`
3. Set the following Env Vars in the Render dashboard:
   - `SECRET_KEY` — a secure random string
   - `ADMIN_PASSWORD` — initial admin password (optional; used to bootstrap DB)
   - `DATABASE_URL` — PostgreSQL connection string if you use Postgres
4. Deploy and check the `logs` if anything fails.

Notes:
- The app exposes a health endpoint at `/health` that Render can use for health checks.
- For production, prefer Postgres over SQLite and use a managed DB service.

## Postgres & data persistence 🔒
- Render provides **Managed PostgreSQL**; create one in the Render dashboard and set `DATABASE_URL` for the web service.
- The application **normalizes `postgres://` → `postgresql://` automatically** (see `papa.py`), but it's best to use a `postgresql://` URL if possible.
- For secure connections, append `?sslmode=require` to the URL if your DB provider requires TLS.

### Quick local Postgres (Docker)
```bash
# Start a temporary Postgres and set DATABASE_URL to test locally
docker run --name no1-db -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres:15
export DATABASE_URL='postgresql://postgres:secret@localhost:5432/postgres'
```

If you have existing data in `local.db` and want a migration, use the provided script `scripts/migrate_sqlite_to_pg.py`.

### Migration example
```bash
# Export target database URL (or pass --target)
export DATABASE_URL='postgresql://user:pass@host:5432/dbname?sslmode=require'
python scripts/migrate_sqlite_to_pg.py --sqlite local.db --target "$DATABASE_URL"
# Add --force to overwrite existing data in target
python scripts/migrate_sqlite_to_pg.py --sqlite local.db --target "$DATABASE_URL" --force
```

### GitHub Actions deploy to Render
A workflow is included at `.github/workflows/deploy-to-render.yml` which triggers a deploy when `main` is pushed.

You must set the following **repository secrets** in GitHub:
- `RENDER_API_KEY` — your Render API key (read-only deploy key is fine)
- `RENDER_SERVICE_ID` — the service id for the Web Service on Render (starts with `srv-`)

> To access the admin view, set the environment variable `ADMIN_PASSWORD` and visit `/admin-login` (or use the admin login form).
