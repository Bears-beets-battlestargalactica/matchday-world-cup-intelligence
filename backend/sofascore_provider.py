"""Cached SofaScore fallback provider for optional roster enrichment.

This provider does not scrape SofaScore live during user requests.
It reads normalized roster JSON files from backend/sofascore_cache/rosters.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT.parent
DEFAULT_CACHE_DIR = ROOT / "sofascore_cache"

TEAM_ALIASES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Bosnia Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Ivory Coast": "Côte d'Ivoire",
    "South Korea": "Korea Republic",
    "United States": "USA",
    "United States of America": "USA",
}


class SofaScoreError(RuntimeError):
    """Cached SofaScore data could not supply a safe roster response."""


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


class SofaScoreProvider:
    def __init__(self) -> None:
        enabled = os.getenv("SOFASCORE_ENABLED", "true").strip().lower()
        self.enabled = enabled not in {"0", "false", "no", "off"}

        configured_dir = os.getenv("SOFASCORE_CACHE_DIR", "").strip()
        cache_dir = Path(configured_dir) if configured_dir else DEFAULT_CACHE_DIR
        if not cache_dir.is_absolute():
            cache_dir = WEB_ROOT / cache_dir

        self.cache_dir = cache_dir
        self.rosters_dir = self.cache_dir / "rosters"

        image_urls = os.getenv("SOFASCORE_IMAGE_URLS", "true").strip().lower()
        self.use_image_urls = image_urls not in {"0", "false", "no", "off"}

    @property
    def configured(self) -> bool:
        return self.enabled and self.rosters_dir.exists()

    def available_teams(self) -> list[str]:
        if not self.rosters_dir.exists():
            return []

        teams = []
        for path in sorted(self.rosters_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue

            team = payload.get("team") or payload.get("provider_team") or path.stem.replace("-", " ").title()
            teams.append(str(team))

        return teams

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "provider": "SofaScore cached rosters" if self.configured else None,
            "cache_dir": str(self.rosters_dir),
            "available_teams": self.available_teams(),
            "live_fetch": False,
        }

    def _candidate_names(self, team_name: str) -> list[str]:
        alias = TEAM_ALIASES.get(team_name, team_name)
        names = [team_name, alias]

        # Also try reverse aliases.
        for source, target in TEAM_ALIASES.items():
            if target.casefold() == team_name.casefold():
                names.append(source)

        unique = []
        for name in names:
            if name and name not in unique:
                unique.append(name)
        return unique

    def _candidate_paths(self, team_name: str) -> list[Path]:
        paths = []
        for name in self._candidate_names(team_name):
            paths.append(self.rosters_dir / f"{slugify(name)}.json")
            paths.append(self.rosters_dir / f"{name}.json")
        return paths

    def _read_roster_payload(self, team_name: str) -> dict:
        if not self.configured:
            raise SofaScoreError("SofaScore cache is not configured.")

        for path in self._candidate_paths(team_name):
            if not path.exists():
                continue
            try:
                return json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                raise SofaScoreError(f"Cached SofaScore roster is unreadable: {path.name}") from error

        # Last chance: scan JSON files and match the team field.
        wanted = {name.casefold() for name in self._candidate_names(team_name)}
        for path in sorted(self.rosters_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue

            payload_team = str(payload.get("team") or payload.get("provider_team") or "").casefold()
            if payload_team in wanted:
                return payload

        raise SofaScoreError(f"No cached SofaScore roster was found for {team_name}.")

    def _photo_url(self, player_id) -> str | None:
        if not self.use_image_urls or not player_id:
            return None
        return f"https://api.sofascore.app/api/v1/player/{player_id}/image"

    def _normalise_player(self, raw: dict) -> dict | None:
        player = raw.get("player") if isinstance(raw.get("player"), dict) else raw

        player_id = (
            player.get("id")
            or player.get("player_id")
            or player.get("sofascore_id")
        )

        name = (
            player.get("name")
            or player.get("shortName")
            or player.get("displayName")
            or player.get("slug")
        )

        if not name:
            return None

        position = player.get("position")
        if isinstance(position, dict):
            position = position.get("name") or position.get("shortName")

        number = (
            player.get("number")
            or player.get("shirtNumber")
            or player.get("jerseyNumber")
        )

        photo = (
            player.get("photo")
            or player.get("image")
            or player.get("imageUrl")
            or player.get("avatar")
            or player.get("avatarUrl")
            or player.get("photo_url")
            or self._photo_url(player_id)
        )

        return {
            "id": player_id,
            "name": name,
            "age": player.get("age"),
            "number": number,
            "position": position or "Player",
            "photo": photo,
            "rating": player.get("rating"),
        }

    def roster(self, team_name: str) -> dict:
        payload = self._read_roster_payload(team_name)

        raw_players = (
            payload.get("players")
            or payload.get("squad")
            or payload.get("roster")
            or []
        )

        players = []
        for raw in raw_players:
            if not isinstance(raw, dict):
                continue
            player = self._normalise_player(raw)
            if player:
                players.append(player)

        if not players:
            raise SofaScoreError(f"Cached SofaScore roster for {team_name} has no usable players.")

        return {
            "team": team_name,
            "provider": "SofaScore cache",
            "provider_team": payload.get("provider_team") or payload.get("team") or team_name,
            "provider_team_id": payload.get("provider_team_id") or payload.get("team_id"),
            "logo": payload.get("logo"),
            "players": players,
            "cached": True,
            "rating_note": "This roster is loaded from cached SofaScore data. It is not used by the Elo + Poisson prediction model.",
        }
