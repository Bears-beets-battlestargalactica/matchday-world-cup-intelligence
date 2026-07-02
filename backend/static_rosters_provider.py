"""Static roster fallback exported from local normalized roster cache."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_ROSTERS_PATH = ROOT / "static_rosters.json"


class StaticRosterError(RuntimeError):
    """Static roster snapshot could not provide a roster."""


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

    def roster(self, team_name: str) -> dict:
        data = self._load()
        roster = data.get(team_name)

        if not roster:
            # Case-insensitive fallback.
            wanted = team_name.casefold()
            for key, value in data.items():
                if key.casefold() == wanted:
                    roster = value
                    break

        if not roster:
            raise StaticRosterError(f"No static roster snapshot found for {team_name}.")

        roster = dict(roster)
        roster["team"] = team_name
        roster["provider"] = "Static roster snapshot"
        roster["cached"] = True
        roster.setdefault(
            "rating_note",
            "This is a static roster snapshot used for visual context only. It does not affect the prediction model.",
        )
        return roster
