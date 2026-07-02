"""Static roster fallback exported from local normalized roster cache."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_ROSTERS_PATH = ROOT / "static_rosters.json"

TEAM_ALIASES = {
    "Cape Verde Islands": "Cape Verde",
    "Cape Verde": "Cape Verde",
    "Curaçao": "Curacao",
    "Curacao": "Curacao",
    "Côte d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Congo DR": "DR Congo",
    "DR Congo": "DR Congo",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "Türkiye": "Turkey",
    "Turkey": "Turkey",
    "United States of America": "United States",
    "USA": "United States",
    "United States": "United States",
    "Czech Republic": "Czechia",
    "Czechia": "Czechia",
}


class StaticRosterError(RuntimeError):
    """Static roster snapshot could not provide a roster."""


def _normalise(value: str) -> str:
    clean = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", clean.casefold())


class StaticRosterProvider:
    def __init__(self) -> None:
        self.path = STATIC_ROSTERS_PATH

    @property
    def configured(self) -> bool:
        return self.path.exists()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError as error:
            raise StaticRosterError("static_rosters.json is not valid JSON.") from error

    def status(self) -> dict:
        data = self._load() if self.configured else {}
        return {
            "configured": self.configured,
            "provider": "Static roster snapshot",
            "path": str(self.path),
            "teams": sorted(data.keys()),
            "team_count": len(data),
        }

    def _resolve_key(self, team_name: str, data: dict) -> str | None:
        requested = team_name.strip()
        candidates = [
            requested,
            TEAM_ALIASES.get(requested, requested),
        ]

        # Exact / case-insensitive match first.
        for candidate in candidates:
            for key in data:
                if key.casefold() == candidate.casefold():
                    return key

        # Accent / punctuation-insensitive match.
        wanted = {_normalise(candidate) for candidate in candidates}
        for key in data:
            if _normalise(key) in wanted:
                return key

        return None

    def roster(self, team_name: str) -> dict:
        data = self._load()
        key = self._resolve_key(team_name, data)

        if not key:
            raise StaticRosterError(f"No static roster snapshot found for {team_name}.")

        roster = dict(data[key])
        roster["team"] = team_name
        roster.setdefault("provider_team", key)
        roster["provider"] = "Static roster snapshot"
        roster["cached"] = True
        roster.setdefault(
            "rating_note",
            "This is a static roster snapshot used for visual context only. It does not affect the prediction model.",
        )
        return roster
