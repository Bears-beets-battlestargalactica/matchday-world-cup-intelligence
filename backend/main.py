"""FastAPI service for Matchday World Cup Intelligence."""

from __future__ import annotations

import os
import random
import re
from collections import Counter
from datetime import datetime, timezone
from math import exp
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .data import fetch_world_cup, seed_matches
from .api_football import ApiFootballError, ApiFootballProvider
from .kickoff import KickoffError, KickoffProvider
from .leaderboard import LeaderboardStore, LeaderboardUnavailable, NicknameTaken
from .model import EloPoissonEngine
from .player_watchlist import PLAYER_WATCHLIST, WATCHLIST_NOTE


WEB_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = WEB_ROOT / "backend" / "matchday.db"
load_dotenv(WEB_ROOT / ".env")
app = FastAPI(title="Matchday Intelligence API", version="0.1.0")

GROUP_CODE = re.compile(r"^GROUP_[A-L]$")


def load_active_fixtures() -> tuple[list, str]:
    """Prefer the live season at boot; keep the demo usable if the provider is down."""
    if os.getenv("FOOTBALL_DATA_API_KEY"):
        try:
            incoming = fetch_world_cup()
            if incoming:
                return incoming, "football-data.org"
        except RuntimeError:
            pass
    return seed_matches(), "historical seed data"


fixtures, fixture_source = load_active_fixtures()
engine = EloPoissonEngine(fixtures)
api_football = ApiFootballProvider()
kickoff = KickoffProvider()
leaderboard_store = LeaderboardStore(DATABASE_PATH)

class PredictionRequest(BaseModel):
    home: str = Field(min_length=2, max_length=80)
    away: str = Field(min_length=2, max_length=80)


class AnalystRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    home: str | None = Field(default=None, max_length=80)
    away: str | None = Field(default=None, max_length=80)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=24)
    token: str | None = Field(default=None, min_length=8, max_length=64)


class LeaderboardPickRequest(BaseModel):
    token: str = Field(min_length=8, max_length=64)
    fixture_key: str = Field(min_length=4, max_length=200)
    prediction: str = Field(pattern="^(home|draw|away)$")


def llm_provider() -> str:
    configured = os.getenv("LLM_PROVIDER", "").strip().lower()
    # OpenRouter keys begin with sk-or-. This keeps a first-time setup usable
    # when a key was pasted into the older OPENAI_API_KEY placeholder.
    if configured == "openrouter" or os.getenv("OPENROUTER_API_KEY", "").strip():
        return "openrouter"
    if os.getenv("OPENAI_API_KEY", "").strip().startswith("sk-or-"):
        return "openrouter"
    return configured or "openai"


def openrouter_api_key() -> str:
    explicit = os.getenv("OPENROUTER_API_KEY", "").strip()
    if explicit:
        return explicit
    legacy = os.getenv("OPENAI_API_KEY", "").strip()
    return legacy if legacy.startswith("sk-or-") else ""


def llm_configured() -> bool:
    if llm_provider() == "openrouter":
        return bool(openrouter_api_key())
    return bool(os.getenv("OPENAI_API_KEY"))


def dashboard_payload() -> dict:
    upcoming = upcoming_fixtures()
    predictions = [fixture_prediction(fixture) for fixture in upcoming[:3]]
    active_group = upcoming[0].group if upcoming and upcoming[0].group else next(iter(group_codes()), None)
    return {
        "source": fixture_source,
        "live_updates_enabled": fixture_source == "football-data.org",
        "matches": predictions,
        "teams": tournament_teams(),
        "standings": engine.standings(active_group) if active_group else [],
        "standings_group": active_group.replace("GROUP_", "Group ") if active_group else "No active group",
        "model": {"name": "Elo + Poisson", "matches_trained": sum(fixture.complete for fixture in fixtures), "features": 5},
    }


def kickoff_is_future(fixture) -> bool:
    if not fixture.kickoff:
        return False
    try:
        kickoff = datetime.fromisoformat(fixture.kickoff.replace("Z", "+00:00"))
        return kickoff > datetime.now(timezone.utc)
    except ValueError:
        return False


def is_group_fixture(fixture) -> bool:
    return fixture.stage in (None, "GROUP_STAGE") and bool(
        fixture.group and (GROUP_CODE.fullmatch(fixture.group) or re.fullmatch(r"[A-L]", fixture.group))
    )
def is_tournament_fixture(fixture) -> bool:
    return bool(fixture.home and fixture.away)

def group_codes() -> list[str]:
    return sorted({fixture.group for fixture in fixtures if is_group_fixture(fixture) and fixture.group})


def tournament_teams() -> list[str]:
    return sorted({team for fixture in fixtures if is_group_fixture(fixture) for team in (fixture.home, fixture.away)})


def upcoming_fixtures() -> list:
    return sorted(
        (
            fixture
            for fixture in fixtures
            if is_tournament_fixture(fixture)
            and not fixture.complete
            and kickoff_is_future(fixture)
        ),
        key=lambda fixture: fixture.kickoff or "9999-12-31T23:59:59Z",
    )

def fixture_prediction(fixture) -> dict:
    prediction = engine.predict(fixture.home, fixture.away).as_dict()
    return {
        **prediction,
        "kickoff": fixture.kickoff,
        "group": fixture.group,
        "stage": fixture.stage,
        "provider_id": getattr(fixture, "provider_id", None),
        "matchday": getattr(fixture, "matchday", None),
    }    
def completed_tournament_fixtures() -> list:
    return sorted(
        (fixture for fixture in fixtures if is_tournament_fixture(fixture) and fixture.complete),
        key=lambda fixture: fixture.kickoff or "",
        reverse=True,
    )

def fixture_actual_outcome(fixture) -> str:
    if fixture.home_goals == fixture.away_goals:
        return "draw"
    if fixture.home_goals > fixture.away_goals:
        return "home"
    return "away"


def prediction_outcome(prediction: dict) -> str:
    if prediction["home_win"] >= prediction["draw"] and prediction["home_win"] >= prediction["away_win"]:
        return "home"
    if prediction["away_win"] >= prediction["draw"]:
        return "away"
    return "draw"


def backtested_fixture_prediction(fixture) -> dict:
    prior_fixtures = [
        item
        for item in fixtures
        if item.complete
        and item.kickoff
        and fixture.kickoff
        and item.kickoff < fixture.kickoff
    ]

    backtest_engine = EloPoissonEngine(prior_fixtures) if prior_fixtures else engine
    prediction = backtest_engine.predict(fixture.home, fixture.away).as_dict()

    actual_outcome = fixture_actual_outcome(fixture)
    predicted_outcome = prediction_outcome(prediction)

    return {
        **prediction,
        "kickoff": fixture.kickoff,
        "group": fixture.group,
        "stage": fixture.stage,
        "status": fixture.status,
        "complete": True,
        "actual_home_goals": fixture.home_goals,
        "actual_away_goals": fixture.away_goals,
        "actual_scoreline": f"{fixture.home_goals}-{fixture.away_goals}",
        "actual_outcome": actual_outcome,
        "predicted_outcome": predicted_outcome,
        "model_correct": actual_outcome == predicted_outcome,
        "prediction_type": "pre-match backtest",
    }


def title_outlook() -> dict:
    """A transparent title power ranking based only on the current Elo ratings.

    This deliberately does not claim to be a fully bracket-aware tournament
    simulation. It is a fast, explainable title-outlook layer for the dashboard.
    """
    teams = tournament_teams()
    if not teams:
        return {"contenders": [], "method": "No teams available."}
    weights = [exp((engine.ratings[team] - max(engine.ratings[item] for item in teams)) / 165) for team in teams]
    randomizer = random.Random(20260622)
    draws = randomizer.choices(teams, weights=weights, k=10000)
    wins = Counter(draws)
    contenders = [
        {"team": team, "title_chance": round(wins[team] / 100, 1), "elo": round(engine.ratings[team])}
        for team in teams
    ]
    contenders.sort(key=lambda row: row["title_chance"], reverse=True)
    return {
        "contenders": contenders[:12],
        "teams": teams,
        "method": "10,000 weighted title draws from current Elo strength. This is a power-ranking outlook, not a bracket-by-bracket guarantee.",
    }


def all_tournament_fixtures() -> list[dict]:
    rows = []
    for fixture in sorted((item for item in fixtures if is_group_fixture(item)), key=lambda item: item.kickoff or "9999-12-31T23:59:59Z"):
        row = {"home": fixture.home, "away": fixture.away, "kickoff": fixture.kickoff, "group": fixture.group, "complete": fixture.complete, "home_goals": fixture.home_goals, "away_goals": fixture.away_goals}
        if not fixture.complete:
            row.update(fixture_prediction(fixture))
        rows.append(row)
    return rows


def fixture_key(fixture) -> str:
    provider_id = getattr(fixture, "provider_id", None)
    if provider_id:
        return str(provider_id)
    return f"{fixture.home}|{fixture.away}|{fixture.kickoff or ''}"


def recent_form(team: str) -> list[dict]:
    matches = sorted(
        (fixture for fixture in fixtures if is_group_fixture(fixture) and fixture.complete and team in (fixture.home, fixture.away)),
        key=lambda fixture: fixture.kickoff or "",
        reverse=True,
    )[:5]
    form = []
    for fixture in matches:
        home_goals, away_goals = fixture.home_goals or 0, fixture.away_goals or 0
        is_home = fixture.home == team
        scored, conceded = (home_goals, away_goals) if is_home else (away_goals, home_goals)
        result = "W" if scored > conceded else "D" if scored == conceded else "L"
        form.append({"opponent": fixture.away if is_home else fixture.home, "score": f"{scored}–{conceded}", "result": result})
    return form


def team_profile(team: str) -> dict:
    players = [player for player in PLAYER_WATCHLIST if player["team"] == team]
    return {
        "team": team,
        "elo": round(engine.ratings[team]),
        "attack_index": round(engine.attack[team], 2),
        "defence_index": round(engine.defence[team], 2),
        "recent_form": recent_form(team),
        "watch_players": players,
    }


@app.get("/")
def home() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(WEB_ROOT / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "provider_configured": bool(os.getenv("FOOTBALL_DATA_API_KEY")),
        "fixture_source": fixture_source,
        "api_football": api_football.status(),
        "kickoff": kickoff.status(),
        "leaderboard": leaderboard_store.status(),
        "llm_configured": llm_configured(),
        "llm_provider": llm_provider() if llm_configured() else None,
    }


@app.get("/api/dashboard")
def dashboard() -> dict:
    return dashboard_payload()


@app.get("/api/schedule")
def schedule(include_completed: bool = False) -> dict:
    """Future fixtures by default; optionally include completed matches with honest backtested forecasts."""
    upcoming = [fixture_prediction(fixture) for fixture in upcoming_fixtures()]

    payload = {
        "matches": upcoming,
        "teams": tournament_teams(),
    }

    if include_completed:
        payload["upcoming"] = upcoming
        payload["completed"] = [
            backtested_fixture_prediction(fixture)
            for fixture in completed_tournament_fixtures()
        ]

    return payload



KNOCKOUT_ROUNDS = [
    ("LAST_32", "Round of 32", 16),
    ("LAST_16", "Round of 16", 8),
    ("QUARTER_FINALS", "Quarterfinals", 4),
    ("SEMI_FINALS", "Semifinals", 2),
    ("FINAL", "Final", 1),
]

KNOCKOUT_STAGE_ORDER = {
    stage: index
    for index, (stage, _, _) in enumerate(KNOCKOUT_ROUNDS)
}

KNOCKOUT_STAGE_LABELS = {stage: label for stage, label, _ in KNOCKOUT_ROUNDS}

KNOCKOUT_STAGE_ALIASES = {
    "LAST_32": "LAST_32",
    "ROUND_OF_32": "LAST_32",
    "R32": "LAST_32",
    "LAST_16": "LAST_16",
    "ROUND_OF_16": "LAST_16",
    "R16": "LAST_16",
    "QUARTER_FINALS": "QUARTER_FINALS",
    "QUARTER_FINAL": "QUARTER_FINALS",
    "QUARTERFINALS": "QUARTER_FINALS",
    "SEMI_FINALS": "SEMI_FINALS",
    "SEMI_FINAL": "SEMI_FINALS",
    "SEMIFINALS": "SEMI_FINALS",
    "FINAL": "FINAL",
}


def canonical_knockout_stage(stage) -> str | None:
    if not stage:
        return None
    return KNOCKOUT_STAGE_ALIASES.get(str(stage).upper())


def knockout_fixture_sort_key(fixture) -> tuple:
    stage = canonical_knockout_stage(fixture.stage)

    return (
        KNOCKOUT_STAGE_ORDER.get(stage, 99),
        getattr(fixture, "matchday", None) or getattr(fixture, "provider_id", None) or 999999,
        fixture.kickoff or "9999-12-31T23:59:59Z",
    )

def knockout_winner(fixture) -> str | None:
    if not fixture.complete:
        return None
    if fixture.home_goals is None or fixture.away_goals is None:
        return None
    if fixture.home_goals > fixture.away_goals:
        return fixture.home
    if fixture.away_goals > fixture.home_goals:
        return fixture.away
    return None


def knockout_scoreline(fixture) -> str | None:
    if fixture.home_goals is None or fixture.away_goals is None:
        return None
    return f"{fixture.home_goals}-{fixture.away_goals}"


def knockout_fixture_row(fixture) -> dict:
    stage = canonical_knockout_stage(fixture.stage)
    winner = knockout_winner(fixture)

    return {
        "key": fixture_key(fixture),
        "provider_id": getattr(fixture, "provider_id", None),
        "matchday": getattr(fixture, "matchday", None),
        "home": fixture.home,
        "away": fixture.away,
        "kickoff": fixture.kickoff,
        "stage": stage,
        "stage_label": KNOCKOUT_STAGE_LABELS.get(stage, "Knockout"),
        "status": fixture.status,
        "complete": bool(fixture.complete),
        "locked": bool(winner),
        "winner": winner,
        "home_goals": fixture.home_goals,
        "away_goals": fixture.away_goals,
        "scoreline": knockout_scoreline(fixture),
    }


def knockout_fixtures() -> list:
    return sorted(
        (
            fixture
            for fixture in fixtures
            if is_tournament_fixture(fixture)
            and canonical_knockout_stage(fixture.stage)
        ),
        key=knockout_fixture_sort_key,
    )


@app.get("/api/bracket")
def bracket() -> dict:
    """Provider-backed knockout bracket.

    Completed knockout matches are locked from actual results.
    Future known fixtures are selectable by the user on the frontend.
    Later unknown slots stay TBD until provider data or user picks fill them.
    """
    rounds = {
        stage: {"stage": stage, "label": label, "target_matches": target, "matches": []}
        for stage, label, target in KNOCKOUT_ROUNDS
    }

    for fixture in knockout_fixtures():
        stage = canonical_knockout_stage(fixture.stage)
        if stage in rounds:
            rounds[stage]["matches"].append(knockout_fixture_row(fixture))

    return {
        "source": fixture_source,
        "rounds": [rounds[stage] for stage, _, _ in KNOCKOUT_ROUNDS],
    }

@app.get("/api/groups")
def groups() -> dict:
    """Current group tables built from completed provider fixtures."""
    tables = []
    for group in group_codes():
        table = engine.standings(group)
        if table:
            tables.append({"name": group.replace("GROUP_", "Group "), "table": table})
    return {"groups": tables}


@app.get("/api/simulations")
def simulations() -> dict:
    """Explain the most decisive and closest upcoming model forecasts."""
    predictions = [fixture_prediction(fixture) for fixture in upcoming_fixtures()[:12]]
    if not predictions:
        return {"forecasts": [], "strongest_favourite": None, "closest_match": None}
    favourite = max(predictions, key=lambda match: max(match["home_win"], match["away_win"]))
    closest = min(predictions, key=lambda match: abs(match["home_win"] - match["away_win"]))
    return {"forecasts": predictions, "strongest_favourite": favourite, "closest_match": closest}


@app.get("/api/tournament")
def tournament() -> dict:
    outlook = title_outlook()
    return {**outlook, "fixtures": all_tournament_fixtures(), "scoring": {"correct_outcome": 3, "correct_champion": 20}}


@app.get("/api/players")
def players() -> dict:
    available_teams = set(tournament_teams())
    watchlist = [player for player in PLAYER_WATCHLIST if player["team"] in available_teams]
    return {"players": watchlist, "note": WATCHLIST_NOTE, "provider": api_football.status()}


@app.get("/api/teams")
def teams() -> dict:
    names = tournament_teams()
    return {
        "teams": [team_profile(team) for team in names],
        "note": WATCHLIST_NOTE,
        "provider": api_football.status(),
        "rating_provider": kickoff.status(),
    }


@app.get("/api/team-roster")
def team_roster(team: str) -> dict:
    """Load one verified squad at a time, with a persistent quota-saving cache."""
    if not team.strip():
        raise HTTPException(status_code=422, detail="Choose a team.")
    if not api_football.configured:
        raise HTTPException(status_code=503, detail="API-Football is not configured.")
    try:
        return api_football.roster(team.strip())
    except ApiFootballError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/player-profile")
def player_profile(team: str, player_id: int) -> dict:
    """Click-to-load 2026 tournament match statistics and average rating."""
    if not team.strip() or player_id <= 0:
        raise HTTPException(status_code=422, detail="Choose a valid team and player.")
    if not api_football.configured:
        raise HTTPException(status_code=503, detail="API-Football is not configured.")
    try:
        if kickoff.configured:
            roster = api_football.roster(team.strip())
            player = next((item for item in roster["players"] if item.get("id") == player_id), None)
            if not player:
                raise ApiFootballError("That player is not in the provider squad snapshot.")
            return kickoff.player_profile(team.strip(), str(player.get("name") or ""), player)
        return api_football.player_profile(team.strip(), player_id)
    except (ApiFootballError, KickoffError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/match-detail")
def match_detail(home: str, away: str) -> dict:
    if not home or not away or home == away:
        raise HTTPException(status_code=422, detail="Choose two different teams.")
    prediction = engine.predict(home, away).as_dict()
    return {
        "prediction": prediction,
        "home_profile": team_profile(home),
        "away_profile": team_profile(away),
        "watch_note": WATCHLIST_NOTE,
        "roster_provider": api_football.status(),
    }


@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict:
    if request.home.strip().lower() == request.away.strip().lower():
        raise HTTPException(status_code=422, detail="Choose two different teams.")
    return engine.predict(request.home.strip(), request.away.strip()).as_dict()


@app.post("/api/leaderboard/register")
def register(request: RegisterRequest) -> dict:
    name = request.name.strip()
    try:
        return leaderboard_store.register(name, request.token)
    except NicknameTaken as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except LeaderboardUnavailable as error:
        raise HTTPException(status_code=503, detail="The public leaderboard is temporarily unavailable.") from error


@app.post("/api/leaderboard/pick")
def submit_pick(request: LeaderboardPickRequest) -> dict:
    valid_keys = {fixture_key(fixture) for fixture in fixtures if not fixture.complete}
    if request.fixture_key not in valid_keys:
        raise HTTPException(status_code=422, detail="That fixture is no longer available for a pick.")
    try:
        name = leaderboard_store.save_pick(request.token, request.fixture_key, request.prediction)
        if not name:
            raise HTTPException(status_code=401, detail="Register a nickname first.")
        return {"saved": True, "name": name}
    except LeaderboardUnavailable as error:
        raise HTTPException(status_code=503, detail="The public leaderboard is temporarily unavailable.") from error


@app.get("/api/leaderboard")
def leaderboard() -> dict:
    results = {}
    for fixture in fixtures:
        if not fixture.complete:
            continue
        home_goals, away_goals = fixture.home_goals or 0, fixture.away_goals or 0
        results[fixture_key(fixture)] = "home" if home_goals > away_goals else "away" if away_goals > home_goals else "draw"
    try:
        rows = leaderboard_store.entries()
    except LeaderboardUnavailable as error:
        raise HTTPException(status_code=503, detail="The public leaderboard is temporarily unavailable.") from error
    scores: dict[str, dict] = {}
    for row in rows:
        score = scores.setdefault(row["name"], {"name": row["name"], "points": 0, "correct": 0, "picks": 0})
        if row["fixture_key"]:
            score["picks"] += 1
            if results.get(row["fixture_key"]) == row["prediction"]:
                score["points"] += 3
                score["correct"] += 1
    table = sorted(scores.values(), key=lambda row: (row["points"], row["correct"], row["picks"]), reverse=True)
    return {"leaders": table[:25], "scoring": "3 points for a correct match outcome. No money or betting."}


@app.post("/api/refresh")
def refresh() -> dict:
    global fixtures, engine, fixture_source
    incoming = fetch_world_cup()
    if not incoming:
        return {"updated": False, "reason": "FOOTBALL_DATA_API_KEY is not configured; retained known historical data."}
    fixtures = incoming
    engine = EloPoissonEngine(fixtures)
    fixture_source = "football-data.org"
    return {"updated": True, "matches_loaded": len(fixtures)}


def local_analyst(question: str, prediction: dict) -> str:
    leading = prediction["home"] if prediction["home_win"] >= prediction["away_win"] else prediction["away"]
    return (
        f"{leading} are the model’s lean: {prediction['home_win']}% / {prediction['draw']}% / {prediction['away_win']}%. "
        f"The most likely scoreline is {prediction['scoreline']} from expected goals of "
        f"{prediction['expected_home_goals']}–{prediction['expected_away_goals']}. "
        f"Key signal: {prediction['factors'][0]}. This is {prediction['confidence'].lower()} confidence."
    )


def local_tournament_analyst(question: str) -> str:
    outlook = title_outlook()
    lower_question = question.lower()
    if any(term in lower_question for term in ("player", "watch", "star", "perform")):
        players = ", ".join(f"{player['player']} ({player['team']})" for player in PLAYER_WATCHLIST[:5])
        return f"Players to watch in the curated context layer: {players}. {WATCHLIST_NOTE}"
    contenders = outlook["contenders"][:4]
    ranking = "; ".join(f"{row['team']} {row['title_chance']}%" for row in contenders)
    leader = contenders[0]
    return f"The current title-outlook leader is {leader['team']} at {leader['title_chance']}%. Top contenders: {ranking}. {outlook['method']}"


@app.post("/api/analyst")
def analyst(request: AnalystRequest) -> dict:
    has_match = bool(request.home and request.away)
    prediction = engine.predict(request.home.strip(), request.away.strip()).as_dict() if has_match else None
    local_answer = local_analyst(request.question, prediction) if prediction else local_tournament_analyst(request.question)
    if not llm_configured():
        return {"answer": local_answer, "mode": "local", "prediction": prediction}
    try:
        from openai import OpenAI

        instructions = (
            "You are a careful football analyst. Explain only the model facts supplied. "
            "Do not claim live injuries, odds, fixtures, or news. State uncertainty plainly."
        )
        prompt = (
            f"User question: {request.question}\n\nModel context:\n{prediction or title_outlook()}\n\n"
            "Answer in at most 110 words, with a clear model-based explanation."
        )
        if llm_provider() == "openrouter":
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_api_key())
            response = client.chat.completions.create(
                model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
                messages=[{"role": "system", "content": instructions}, {"role": "user", "content": prompt}],
                max_tokens=220,
            )
            answer = response.choices[0].message.content or local_answer
            mode = "openrouter"
        else:
            client = OpenAI()
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), instructions=instructions, input=prompt
            )
            answer = response.output_text
            mode = "openai"
        return {"answer": answer, "mode": mode, "prediction": prediction, "outlook": None if prediction else title_outlook()}
    except Exception:
        # The core forecast stays usable if a key is missing, quota is exhausted, or a request fails.
        return {"answer": local_answer, "mode": "local-fallback", "prediction": prediction, "outlook": None if prediction else title_outlook()}
