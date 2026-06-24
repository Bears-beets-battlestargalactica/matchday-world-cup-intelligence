"""KickoffAPI adapter for current World Cup player-match statistics.

API-Football remains responsible for on-demand roster snapshots and photos.
KickoffAPI supplies the 2026 tournament statistics and ratings, which are kept
separate from the Elo + Poisson prediction model.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

import certifi
import httpx


CACHE_PATH = Path(__file__).resolve().parent / "kickoff_cache.json"
BASE_URL = "https://api.kickoffapi.com/api/v1"
WORLD_CUP_LEAGUE_ID = 1
CURRENT_WORLD_CUP_SEASON = 2026
COMPLETE_STATUSES = {"FT", "AET", "PEN"}
TEAM_ALIASES = {
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Ivory Coast": "Côte d'Ivoire",
    "South Korea": "Korea Republic",
    "Turkey": "Türkiye",
}


class KickoffError(RuntimeError):
    """KickoffAPI could not provide a reliable current-tournament response."""


def _normalise(value: str) -> str:
    clean = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9 ]", "", clean.casefold()).strip()


def _same_player(left: str, right: str) -> bool:
    """Match provider player names without pretending an ambiguous match is exact."""
    a, b = _normalise(left).split(), _normalise(right).split()
    if not a or not b:
        return False
    if a == b:
        return True
    # Provider A may use "L. Messi" while provider B uses "Lionel Messi".
    return a[-1] == b[-1] and len(a[-1]) > 2 and a[0][0] == b[0][0]


class KickoffProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("KICKOFF_API_KEY", "").strip()
        self.remaining_requests: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "provider": "KickoffAPI" if self.configured else None,
            "season": CURRENT_WORLD_CUP_SEASON,
            "cache_policy": "2026 fixture and player-stat lookups are cached to conserve the request allowance.",
            "remaining_requests": self.remaining_requests,
        }

    def _read_cache(self) -> dict:
        try:
            return json.loads(CACHE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_cache(self, cache: dict) -> None:
        try:
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))
        except OSError:
            pass

    def _get(self, endpoint: str, params: dict[str, str | int] | None = None, ttl_seconds: int = 21_600) -> tuple[dict, bool]:
        if not self.configured:
            raise KickoffError("KickoffAPI is not configured.")
        params = params or {}
        cache_key = f"{endpoint}?{urlencode(sorted(params.items()))}"
        cache = self._read_cache()
        saved = cache.get(cache_key)
        now = time.time()
        if saved and now - saved.get("saved_at", 0) < ttl_seconds:
            return saved["payload"], True
        try:
            response = httpx.get(
                f"{BASE_URL}{endpoint}",
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=18,
                verify=certifi.where(),
            )
            self.remaining_requests = response.headers.get("x-ratelimit-remaining")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise KickoffError("KickoffAPI could not be reached right now.") from error
        if not isinstance(payload, dict) or payload.get("errors"):
            raise KickoffError("KickoffAPI did not return current tournament player data.")
        cache[cache_key] = {"saved_at": now, "payload": payload}
        self._write_cache(cache)
        return payload, False

    def _team(self, team_name: str) -> tuple[int, str, bool]:
        teams_payload, cached = self._get(
            "/teams", {"league": WORLD_CUP_LEAGUE_ID, "season": CURRENT_WORLD_CUP_SEASON}, ttl_seconds=43_200
        )
        desired = _normalise(TEAM_ALIASES.get(team_name, team_name))
        rows = teams_payload.get("response", [])
        selected = next((row for row in rows if _normalise(row.get("name", "")) == desired), None)
        if not selected:
            raise KickoffError(f"KickoffAPI has no 2026 World Cup team match for {team_name}.")
        return int(selected["id"]), str(selected.get("name") or team_name), cached

    def player_profile(self, team_name: str, player_name: str, player: dict) -> dict:
        """Return a transparent 2026-only aggregate for one roster player."""
        team_id, provider_team, teams_cached = self._team(team_name)
        fixture_payload, fixtures_cached = self._get(
            "/fixtures",
            {"team": team_id, "league": WORLD_CUP_LEAGUE_ID, "season": CURRENT_WORLD_CUP_SEASON},
            ttl_seconds=1_800,
        )
        completed = [row for row in fixture_payload.get("response", []) if row.get("statusShort") in COMPLETE_STATUSES]
        if not completed:
            return {
                "player": player,
                "fixture": {"competition": "World Cup 2026", "matches": 0},
                "statistics": None,
                "coverage": {"available": True, "season": CURRENT_WORLD_CUP_SEASON},
                "cached": teams_cached and fixtures_cached,
                "rating_note": "KickoffAPI has no completed 2026 World Cup fixture for this team yet.",
            }

        totals = {"appearances": 0, "minutes": 0, "goals": 0, "assists": 0, "shots": 0, "passes": 0, "tackles": 0}
        ratings: list[float] = []
        accuracies: list[float] = []
        cached = teams_cached and fixtures_cached
        for fixture in completed:
            fixture_id = fixture.get("id")
            if not fixture_id:
                continue
            stats_payload, stats_cached = self._get(f"/fixtures/{fixture_id}/players", ttl_seconds=3_600)
            cached = cached and stats_cached
            entries = [
                row for row in stats_payload.get("response", [])
                if int(row.get("teamId") or 0) == team_id and _same_player((row.get("player") or {}).get("name", ""), player_name)
            ]
            if not entries:
                continue
            statistics = (entries[0].get("statistics") or [{}])[0]
            games, goals, shots, passes, tackles = (
                statistics.get("games", {}), statistics.get("goals", {}), statistics.get("shots", {}),
                statistics.get("passes", {}), statistics.get("tackles", {}),
            )
            totals["appearances"] += 1
            for key, value in (
                ("minutes", games.get("minutes")), ("goals", goals.get("total")), ("assists", goals.get("assists")),
                ("shots", shots.get("total")), ("passes", passes.get("total")), ("tackles", tackles.get("total")),
            ):
                try:
                    totals[key] += int(value or 0)
                except (TypeError, ValueError):
                    pass
            for value, bucket in ((games.get("rating"), ratings), (passes.get("accuracy"), accuracies)):
                try:
                    bucket.append(float(value))
                except (TypeError, ValueError):
                    pass
        fixture_context = {"competition": "World Cup 2026", "matches": len(completed), "team": provider_team}
        if not totals["appearances"]:
            return {
                "player": player,
                "fixture": fixture_context,
                "statistics": None,
                "coverage": {"available": True, "season": CURRENT_WORLD_CUP_SEASON},
                "cached": cached,
                "rating_note": "KickoffAPI has no recorded 2026 World Cup appearance for this player yet.",
            }
        return {
            "player": player,
            "fixture": fixture_context,
            "statistics": {
                "rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
                "appearances": totals["appearances"], "minutes": totals["minutes"], "goals": totals["goals"],
                "assists": totals["assists"], "shots": totals["shots"], "passes": totals["passes"],
                "pass_accuracy": f"{round(sum(accuracies) / len(accuracies))}%" if accuracies else None,
                "tackles": totals["tackles"],
            },
            "coverage": {"available": True, "season": CURRENT_WORLD_CUP_SEASON},
            "cached": cached,
            "rating_note": f"Average match-stat rating across {totals['appearances']} recorded 2026 World Cup appearance(s), supplied by KickoffAPI. It is not a global ranking and is never fed into the prediction model.",
        }
