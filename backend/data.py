"""Known historical World Cup results plus a provider adapter for current data."""

from __future__ import annotations

import json
import os
import ssl
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


ROOT = Path(__file__).resolve().parent
SEED_PATH = ROOT / "seed_matches.json"


@dataclass(frozen=True)
class Fixture:
    home: str
    away: str
    kickoff: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    group: str | None = None
    stage: str | None = None
    status: str | None = None
    provider_id: int | None = None
    matchday: int | None = None
    
    @property
    def complete(self) -> bool:
        return self.status in {"FINISHED", "AWARDED"} or (
            self.home_goals is not None and self.away_goals is not None
        )


def seed_matches() -> list[Fixture]:
    """Load real 2022 FIFA World Cup final-tournament scorelines."""
    rows = json.loads(SEED_PATH.read_text())
    return [Fixture(**row) for row in rows]


def fetch_world_cup() -> list[Fixture]:
    """Fetch FIFA World Cup fixtures from football-data.org when configured.

    The provider requires an API key. Requests use the official competition code
    `WC`; callers can keep using seed data if a key is intentionally absent.
    """
    token = os.getenv("FOOTBALL_DATA_API_KEY")
    if not token:
        return []
    request = Request(
        "https://api.football-data.org/v4/competitions/WC/matches",
        headers={"X-Auth-Token": token, "User-Agent": "matchday-intelligence/1.0"},
    )
    try:
        # Some local Python installations do not inherit the operating system's
        # certificate bundle. certifi keeps provider traffic TLS-verified.
        with urlopen(request, timeout=12, context=ssl.create_default_context(cafile=certifi.where())) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Fixture provider unavailable: {exc}") from exc

    fixtures: list[Fixture] = []
    for match in payload.get("matches", []):
        home = match.get("homeTeam", {}).get("name")
        away = match.get("awayTeam", {}).get("name")
        score = match.get("score", {}).get("fullTime", {})
        if home and away:
            fixtures.append(
                Fixture(
                    home=home,
                    away=away,
                    kickoff=match.get("utcDate"),
                    home_goals=score.get("home"),
                    away_goals=score.get("away"),
                    group=match.get("group"),
                    stage=match.get("stage"),
                    status=match.get("status"),
                    provider_id=match.get("id"),
                    matchday=match.get("matchday"),
                )
            )
    return fixtures
