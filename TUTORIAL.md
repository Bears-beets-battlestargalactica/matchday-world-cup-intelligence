# Matchday: quick tutorial

## 1. Where the website is hosted now

The site is currently running **locally on your Mac** at:

`http://127.0.0.1:8000`

That address works only on this computer while the FastAPI server is running. It is not public yet.

## 2. Open the dashboard

Open this address in your browser:

`http://127.0.0.1:8000`

If the server is ever stopped, start it again from Terminal:

```bash
cd /Users/jibinvarghese/Documents/Codex/2026-06-22/ca/outputs
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

Leave that Terminal window open while using the site. Stop it with `Ctrl+C`.

## 3. What already works without any keys

- Dashboard and match forecasts
- Elo + Poisson model predictions
- Historical 2022 World Cup seed results
- Group table calculation
- AI analyst fallback that explains the model’s actual numbers

The fallback is deliberately grounded in the model output, so it never pretends to know current injuries or live scores.

## 4. Turn on real World Cup fixtures and results

1. Create an account at football-data.org and obtain an API token.
2. The project already has a local `.env` file (it is ignored by Git). Open it and add your token:

```bash
FOOTBALL_DATA_API_KEY=your_token_here
```

3. Restart the server. It loads `.env` automatically:

```bash
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

4. Ask the backend to refresh from the provider:

```bash
curl -X POST http://127.0.0.1:8000/api/refresh
```

When a token is configured, the dashboard badge changes from **Historical data mode** to **Live fixture provider enabled**.

## 5. Turn on the OpenAI analyst

Add your OpenAI key to the same `.env` file:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Restart the server using the command in the prior step. The **Ask the AI analyst** box will then call the model through the backend—your browser never sees the API key.

If the model call is unavailable, the app falls back to a local explanation based on the exact prediction output.

## 6. Useful API endpoints

| Endpoint | What it does |
| --- | --- |
| `GET /api/health` | Shows whether data and LLM keys are configured. |
| `GET /api/dashboard` | Returns the dashboard’s matches, standings, and model metadata. |
| `POST /api/predict` | Produces a forecast for any two team names. |
| `POST /api/analyst` | Produces a model-grounded natural-language explanation. |
| `POST /api/refresh` | Pulls current World Cup matches from the configured provider. |
| `GET /api/team-roster?team=France` | Loads one cached, verified API-Football squad for the Player guide. |

For example:

```bash
curl -X POST http://127.0.0.1:8000/api/predict \
  -H 'Content-Type: application/json' \
  -d '{"home":"Brazil","away":"Morocco"}'
```

## 7. Enable verified squads and a persistent leaderboard

The Player guide now uses API-Football only when you press **Load verified squad** for a selected team. The response is stored locally for 12 hours so browsing teams does not spend the free quota unnecessarily. API-Football roster data is displayed as context and never changes the Elo + Poisson prediction.

When `DATABASE_URL` is set, the leaderboard uses Supabase Postgres rather than the local `matchday.db` file. The app automatically creates the required tables and enables Row Level Security; the browser cannot read the tables directly.

For now, registration is a persistent nickname plus a private token stored in the browser. Email or magic-link accounts are a separate enhancement that needs Supabase's publishable key and Auth redirect settings.

## 8. Publish it publicly later

The project now includes a Render Blueprint and a deployment guide: [DEPLOY_RENDER.md](DEPLOY_RENDER.md). Add environment variables in Render’s dashboard instead of uploading `.env`.

For a stronger portfolio version, deploy the API to AWS App Runner or ECS and move the frontend to S3 + CloudFront. Keep OpenAI and football-data tokens in a secrets manager.
