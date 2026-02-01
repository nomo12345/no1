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

> To access the admin view, set the environment variable `ADMIN_PASSWORD` and visit `/admin-login` (or use the admin login form).
