# Publish Matchday on Render

This folder is deployment-ready. Supply secrets in Render's dashboard; never commit `.env`.

## 1. Create a GitHub repository

Create a new private or public repository, then upload the **contents** of this `outputs` folder so that `render.yaml`, `index.html`, and `backend/` are at the repository root.

## 2. Create the web service

1. Sign in to [Render](https://render.com/).
2. Choose **New +** → **Blueprint** and connect the GitHub repository.
3. Render reads `render.yaml`, installs `backend/requirements.txt`, starts FastAPI, and provides a public `onrender.com` URL.
4. Add any services you use as Render environment variables: `OPENAI_API_KEY`, `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`, and `DATABASE_URL`.

For the current nickname-based leaderboard, `DATABASE_URL` is the only Supabase value the deployed backend needs. Keep `SUPABASE_SERVICE_ROLE_KEY` private and add it only when the app grows into a Supabase Auth account system.

Render's `sync: false` entries intentionally keep those values out of `render.yaml` and Git.

## 3. Verify deployment

After deployment, open:

```text
https://YOUR-SERVICE.onrender.com/api/health
```

Expected result after the configured providers are added:

```json
{"status":"ok","provider_configured":true,"api_football":{"configured":true},"leaderboard":{"mode":"supabase-postgres","configured":true},"llm_configured":true}
```

Then visit the service root to use the dashboard. The server receives the secret keys; the browser does not.

## 4. Refresh real fixture data

Use the deployed URL after setting `FOOTBALL_DATA_API_KEY`:

```bash
curl -X POST https://YOUR-SERVICE.onrender.com/api/refresh
```

## Local run

The app automatically reads `outputs/.env` when it starts. Add your keys to that file, then run:

```bash
cd /Users/jibinvarghese/Documents/Codex/2026-06-22/ca/outputs
.venv/bin/uvicorn backend.main:app --reload --port 8000
```
