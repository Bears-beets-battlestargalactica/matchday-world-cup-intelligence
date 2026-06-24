# Matchday World Cup Intelligence

A FastAPI-backed World Cup prediction prototype with a transparent Elo + Poisson engine, live-fixture provider adapter, and optional OpenAI analyst.

## Run locally

```bash
cd /Users/jibinvarghese/Documents/Codex/2026-06-22/ca/outputs
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

Then open `http://127.0.0.1:8000`.

## Configuration

- The app loads `outputs/.env` automatically. `FOOTBALL_DATA_API_KEY` enables `POST /api/refresh`, which fetches current World Cup fixtures/results from football-data.org.
- `OPENAI_API_KEY` enables the natural-language analyst through `POST /api/analyst`; otherwise the API returns a grounded local explanation. Alternatively use `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL=openrouter/free` to call OpenRouter without exposing a key in the browser.
- `API_FOOTBALL_KEY` enables on-demand verified team roster snapshots and player photos in the Player guide. A squad is fetched only when a visitor asks for it and then cached.
- `KICKOFF_API_KEY` enables 2026 World Cup player-match statistics and average ratings across completed tournament appearances. Those ratings are contextual and never alter the Elo + Poisson model.
- `DATABASE_URL` switches the leaderboard from local SQLite to Supabase Postgres. The backend creates its `users` and `picks` tables and enables Row Level Security. `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are reserved for a later email/magic-link account upgrade and must remain backend-only.

The included seed is a small set of known 2022 World Cup scorelines. It makes the model runnable without credentials, but is intentionally not presented as current tournament data.

To deploy publicly, see [DEPLOY_RENDER.md](DEPLOY_RENDER.md).
