"""Small, cached API-Football adapter used for optional roster enrichment."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import certifi
import httpx


CACHE_PATH = Path(__file__).resolve().parent / "api_football_cache.json"
BASE_URL = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1
CURRENT_WORLD_CUP_SEASON = 2026
TEAM_ALIASES = {
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "Congo DR",
    "Ivory Coast": "Côte d'Ivoire",
    "South Korea": "Korea Republic",
    "Turkey": "Türkiye",
}


class ApiFootballError(RuntimeError):
    """The provider could not supply a safe roster response."""


class ApiFootballCoverageUnavailable(ApiFootballError):
    """The configured provider plan does not include the requested season."""


class ApiFootballProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_FOOTBALL_KEY", "").strip()
        self.remaining_requests: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "provider": "API-Football" if self.configured else None,
            "cache_policy": "Roster lookups are cached for 12 hours to conserve the free daily request allowance.",
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
            # Caching is a quota-saving optimisation, not a reason to fail a page.
            pass

    def _get(self, endpoint: str, params: dict[str, str | int], ttl_seconds: int = 43_200) -> tuple[dict, bool]:
        if not self.configured:
            raise ApiFootballError("API-Football is not configured.")
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
                headers={"x-apisports-key": self.api_key},
                timeout=12,
                verify=certifi.where(),
            )
            self.remaining_requests = response.headers.get("x-ratelimit-requests-remaining")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ApiFootballError("API-Football could not be reached right now.") from error

        if payload.get("errors"):
            if any(key in payload["errors"] for key in ("plan", "season")):
                raise ApiFootballCoverageUnavailable("Current-season player statistics are not included in this API-Football plan.")
            raise ApiFootballError("API-Football did not return roster data for this team.")
        cache[cache_key] = {"saved_at": now, "payload": payload}
        self._write_cache(cache)
        return payload, False

    @staticmethod
    def _pick_team(response: list[dict], requested_name: str) -> dict | None:
        desired = TEAM_ALIASES.get(requested_name, requested_name).casefold()
        national = [row for row in response if row.get("team", {}).get("national")]
        candidates = national or response
        for row in candidates:
            if row.get("team", {}).get("name", "").casefold() == desired:
                return row
        return candidates[0] if candidates else None

    def roster(self, team_name: str) -> dict:
        search_name = TEAM_ALIASES.get(team_name, team_name)
        teams_payload, team_cached = self._get("/teams", {"search": search_name})
        selected = self._pick_team(teams_payload.get("response", []), team_name)
        if not selected:
            raise ApiFootballError("No API-Football national-team roster was found for this team.")

        provider_team = selected["team"]
        roster_payload, roster_cached = self._get("/players/squads", {"team": provider_team["id"]})
        squads = roster_payload.get("response", [])
        squad = next((row for row in squads if row.get("team", {}).get("id") == provider_team["id"]), squads[0] if squads else {})
        players = []
        for row in squad.get("players", []):
            players.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "age": row.get("age"),
                    "number": row.get("number"),
                    "position": row.get("position"),
                    "photo": row.get("photo"),
                    "rating": None,
                }
            )
        return {
            "team": team_name,
            "provider_team": provider_team.get("name"),
            "provider_team_id": provider_team.get("id"),
            "logo": provider_team.get("logo"),
            "players": players,
            "cached": team_cached and roster_cached,
            "rating_note": "This is an API-Football squad snapshot, not a confirmed 2026 final roster. Current 2026 match ratings are shown only when the configured provider plan includes that season; they are never used by this prediction model.",
        }

    def player_profile(self, team_name: str, player_id: int) -> dict:
        """Aggregate a player's 2026 World Cup match statistics, on demand."""
        roster = self.roster(team_name)
        team_id = roster.get("provider_team_id")
        player = next((item for item in roster["players"] if item.get("id") == player_id), None)
        if not team_id or not player:
            raise ApiFootballError("That player is not in the provider squad snapshot.")

        try:
            fixture_payload, fixture_cached = self._get(
                "/fixtures", {"team": team_id, "league": WORLD_CUP_LEAGUE_ID, "season": CURRENT_WORLD_CUP_SEASON}, ttl_seconds=1_800
            )
        except ApiFootballCoverageUnavailable:
            return {
                "player": player,
                "fixture": None,
                "statistics": None,
                "coverage": {"available": False, "season": CURRENT_WORLD_CUP_SEASON},
                "rating_note": "2026 World Cup player statistics are unavailable on the current API-Football plan, so no historical rating is substituted.",
            }

        covered = [row for row in fixture_payload.get("response", []) if row.get("fixture", {}).get("status", {}).get("short") in {"FT", "AET", "PEN"}]
        if not covered:
            return {"player": player, "fixture": {"competition": "World Cup 2026", "matches": 0}, "statistics": None, "coverage": {"available": True, "season": CURRENT_WORLD_CUP_SEASON}, "cached": fixture_cached, "rating_note": "No completed 2026 World Cup match statistics are available for this player yet."}

        totals = {"appearances": 0, "minutes": 0, "goals": 0, "assists": 0, "shots": 0, "passes": 0, "tackles": 0}
        ratings: list[float] = []
        accuracies: list[float] = []
        cached = fixture_cached
        try:
            for fixture in covered:
                fixture_id = fixture.get("fixture", {}).get("id")
                if not fixture_id:
                    continue
                stats_payload, stats_cached = self._get("/fixtures/players", {"fixture": fixture_id}, ttl_seconds=1_800)
                cached = cached and stats_cached
                side = next((item for item in stats_payload.get("response", []) if item.get("team", {}).get("id") == team_id), None)
                selected = next((item for item in (side or {}).get("players", []) if item.get("player", {}).get("id") == player_id), None)
                if not selected:
                    continue
                statistics = (selected.get("statistics") or [{}])[0]
                games, shots, passes, tackles, goals_data = (statistics.get("games", {}), statistics.get("shots", {}), statistics.get("passes", {}), statistics.get("tackles", {}), statistics.get("goals", {}))
                totals["appearances"] += 1
                for key, value in (("minutes", games.get("minutes")), ("goals", goals_data.get("total")), ("assists", goals_data.get("assists")), ("shots", shots.get("total")), ("passes", passes.get("total")), ("tackles", tackles.get("total"))):
                    try:
                        totals[key] += int(value or 0)
                    except (TypeError, ValueError):
                        pass
                for value, bucket in ((games.get("rating"), ratings), (passes.get("accuracy"), accuracies)):
                    try:
                        bucket.append(float(value))
                    except (TypeError, ValueError):
                        pass
        except ApiFootballCoverageUnavailable:
            return {"player": player, "fixture": None, "statistics": None, "coverage": {"available": False, "season": CURRENT_WORLD_CUP_SEASON}, "rating_note": "2026 World Cup player statistics are unavailable on the current API-Football plan, so no historical rating is substituted."}

        if not totals["appearances"]:
            return {"player": player, "fixture": {"competition": "World Cup 2026", "matches": len(covered)}, "statistics": None, "coverage": {"available": True, "season": CURRENT_WORLD_CUP_SEASON}, "cached": cached, "rating_note": "This player has no recorded 2026 World Cup appearance in the provider data yet."}
        return {
            "player": player,
            "fixture": {"competition": "World Cup 2026", "matches": len(covered)},
            "statistics": {
                "rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
                "appearances": totals["appearances"],
                "minutes": totals["minutes"],
                "goals": totals["goals"],
                "assists": totals["assists"],
                "shots": totals["shots"],
                "passes": totals["passes"],
                "pass_accuracy": f"{round(sum(accuracies) / len(accuracies))}%" if accuracies else None,
                "tackles": totals["tackles"],
            },
            "cached": cached,
            "coverage": {"available": True, "season": CURRENT_WORLD_CUP_SEASON},
            "rating_note": f"This is the average match-stat rating across {totals['appearances']} recorded 2026 World Cup appearance(s). It is not a global player ranking and is never fed into the prediction model.",
        }
