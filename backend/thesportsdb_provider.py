"""TheSportsDB fallback provider for player photos and metadata.

This is a lightweight free-tier integration:
- uses TheSportsDB V1 API
- searches known player names one at a time
- caches responses locally
- returns the same broad shape as the roster provider
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT.parent
DEFAULT_CACHE_DIR = ROOT / "thesportsdb_cache"

DEFAULT_API_KEY = "123"
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 30

TEAM_PLAYER_SEEDS = {
    "Argentina": [
        "Lionel Messi",
        "Emiliano Martinez",
        "Julian Alvarez",
        "Lautaro Martinez",
        "Alexis Mac Allister",
        "Rodrigo De Paul",
        "Enzo Fernandez",
        "Cristian Romero",
    ],
    "Portugal": [
        "Cristiano Ronaldo",
        "Bruno Fernandes",
        "Bernardo Silva",
        "Diogo Costa",
        "Joao Cancelo",
        "Ruben Dias",
        "Rafael Leao",
    ],
    "France": [
        "Kylian Mbappe",
        "Antoine Griezmann",
        "Ousmane Dembele",
        "Aurelien Tchouameni",
        "Mike Maignan",
        "William Saliba",
    ],
    "England": [
        "Harry Kane",
        "Jude Bellingham",
        "Bukayo Saka",
        "Phil Foden",
        "Declan Rice",
        "Jordan Pickford",
    ],
    "Brazil": [
        "Vinicius Junior",
        "Rodrygo",
        "Alisson",
        "Marquinhos",
        "Casemiro",
        "Bruno Guimaraes",
    ],
    "Spain": [
        "Lamine Yamal",
        "Pedri",
        "Gavi",
        "Rodri",
        "Dani Olmo",
        "Unai Simon",
    ],
    "Germany": [
        "Jamal Musiala",
        "Florian Wirtz",
        "Joshua Kimmich",
        "Kai Havertz",
        "Antonio Rudiger",
        "Manuel Neuer",
    ],
    "Belgium": [
        "Kevin De Bruyne",
        "Romelu Lukaku",
        "Thibaut Courtois",
        "Jeremy Doku",
        "Youri Tielemans",
        "Amadou Onana",
    ],
    "Netherlands": [
        "Virgil van Dijk",
        "Frenkie de Jong",
        "Cody Gakpo",
        "Xavi Simons",
        "Memphis Depay",
        "Denzel Dumfries",
    ],
    "Croatia": [
        "Luka Modric",
        "Mateo Kovacic",
        "Josko Gvardiol",
        "Andrej Kramaric",
        "Dominik Livakovic",
    ],
    "United States": [
        "Christian Pulisic",
        "Weston McKennie",
        "Tyler Adams",
        "Gio Reyna",
        "Yunus Musah",
        "Matt Turner",
    ],
    "Mexico": [
        "Hirving Lozano",
        "Edson Alvarez",
        "Raul Jimenez",
        "Santiago Gimenez",
        "Guillermo Ochoa",
    ],
    "Morocco": [
        "Achraf Hakimi",
        "Hakim Ziyech",
        "Sofyan Amrabat",
        "Yassine Bounou",
        "Noussair Mazraoui",
    ],
    "Canada": [
        "Alphonso Davies",
        "Jonathan David",
        "Tajon Buchanan",
        "Stephen Eustaquio",
        "Cyle Larin",
    ],
    "Norway": [
        "Erling Haaland",
        "Martin Odegaard",
        "Alexander Sorloth",
        "Oscar Bobb",
    ],
    "Japan": [
        "Kaoru Mitoma",
        "Takefusa Kubo",
        "Wataru Endo",
        "Daichi Kamada",
        "Takumi Minamino",
    ],
    "Switzerland": [
        "Granit Xhaka",
        "Manuel Akanji",
        "Xherdan Shaqiri",
        "Yann Sommer",
        "Breel Embolo",
    ],
    "Colombia": [
        "Luis Diaz",
        "James Rodriguez",
        "Davinson Sanchez",
        "Jhon Duran",
    ],
    "Ghana": [
        "Mohammed Kudus",
        "Thomas Partey",
        "Inaki Williams",
        "Jordan Ayew",
    ],
    "Senegal": [
        "Sadio Mane",
        "Kalidou Koulibaly",
        "Edouard Mendy",
        "Nicolas Jackson",
        "Ismaila Sarr",
    ],
    "Uruguay": [
        "Federico Valverde",
        "Darwin Nunez",
        "Ronald Araujo",
        "Luis Suarez",
        "Jose Maria Gimenez",
    ],
    "Austria": [
        "David Alaba",
        "Marcel Sabitzer",
        "Marko Arnautovic",
        "Christoph Baumgartner",
    ],
    "Algeria": [
        "Riyad Mahrez",
        "Ismael Bennacer",
        "Said Benrahma",
        "Rayan Ait-Nouri",
    ],
    "Egypt": [
        "Mohamed Salah",
        "Omar Marmoush",
        "Mohamed Elneny",
        "Mostafa Mohamed",
    ],
    "Australia": [
        "Mathew Ryan",
        "Jackson Irvine",
        "Craig Goodwin",
        "Harry Souttar",
    ],
    "Cape Verde": [
        "Ryan Mendes",
        "Bebe",
        "Garry Rodrigues",
        "Logan Costa",
    ],
    "DR Congo": [
        "Yoane Wissa",
        "Chancel Mbemba",
        "Cedric Bakambu",
        "Arthur Masuaku",
    ],
    "Ivory Coast": [
        "Sebastien Haller",
        "Franck Kessie",
        "Simon Adingra",
        "Nicolas Pepe",
    ],
    "Paraguay": [
        "Miguel Almiron",
        "Julio Enciso",
        "Gustavo Gomez",
        "Ramon Sosa",
    ],
}


class TheSportsDBError(RuntimeError):
    """TheSportsDB could not provide usable player data."""


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def clean_name(value: str) -> str:
    return (
        value.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ã", "a")
        .replace("ç", "c")
        .replace("ñ", "n")
    )


class TheSportsDBProvider:
    def __init__(self) -> None:
        enabled = os.getenv("THESPORTSDB_ENABLED", "true").strip().lower()
        self.enabled = enabled not in {"0", "false", "no", "off"}

        self.api_key = os.getenv("THESPORTSDB_API_KEY", DEFAULT_API_KEY).strip() or DEFAULT_API_KEY
        self.base_url = f"https://www.thesportsdb.com/api/v1/json/{self.api_key}"

        configured_dir = os.getenv("THESPORTSDB_CACHE_DIR", "").strip()
        cache_dir = Path(configured_dir) if configured_dir else DEFAULT_CACHE_DIR
        if not cache_dir.is_absolute():
            cache_dir = WEB_ROOT / cache_dir

        self.cache_dir = cache_dir
        self.players_dir = self.cache_dir / "players"
        self.ttl_seconds = int(os.getenv("THESPORTSDB_CACHE_TTL_SECONDS", str(DEFAULT_TTL_SECONDS)))

        timeout = os.getenv("THESPORTSDB_TIMEOUT", "8").strip()
        self.timeout = float(timeout)

    @property
    def configured(self) -> bool:
        return self.enabled

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "provider": "TheSportsDB",
            "api_key": "free-v1-123" if self.api_key == DEFAULT_API_KEY else "custom",
            "cache_dir": str(self.players_dir),
            "seeded_teams": sorted(TEAM_PLAYER_SEEDS.keys()),
            "cache_policy": "Player lookups are cached for 30 days by default.",
        }

    def _cache_path(self, player_name: str) -> Path:
        return self.players_dir / f"{slugify(player_name)}.json"

    def _read_cache(self, player_name: str) -> dict | None:
        path = self._cache_path(player_name)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None

        fetched_at = payload.get("_fetched_at", 0)
        if fetched_at and time.time() - fetched_at <= self.ttl_seconds:
            return payload

        return None

    def _write_cache(self, player_name: str, payload: dict) -> None:
        self.players_dir.mkdir(parents=True, exist_ok=True)
        payload["_fetched_at"] = int(time.time())
        self._cache_path(player_name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    def _search_player(self, player_name: str) -> dict | None:
        cached = self._read_cache(player_name)
        if cached is not None:
            return cached

        url = f"{self.base_url}/searchplayers.php?p={quote_plus(clean_name(player_name))}"
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": "Matchday-World-Cup-Intelligence/1.0"},
        )

        if response.status_code == 429:
            raise TheSportsDBError("TheSportsDB rate limit reached. Try again shortly.")

        if response.status_code >= 400:
            raise TheSportsDBError(f"TheSportsDB returned HTTP {response.status_code}.")

        payload = response.json()
        self._write_cache(player_name, payload)
        return payload

    def _pick_player(self, player_name: str, team_name: str, payload: dict) -> dict | None:
        players = payload.get("player") or payload.get("players") or []
        if not isinstance(players, list):
            return None

        wanted = clean_name(player_name).casefold()
        team_wanted = team_name.casefold()

        # Prefer exact/near name matches, then team match if available.
        candidates = []
        for player in players:
            if not isinstance(player, dict):
                continue

            names = [
                player.get("strPlayer"),
                player.get("strPlayerAlternate"),
                player.get("strPlayerShort"),
            ]
            name_blob = " ".join(str(name or "") for name in names)
            name_blob_clean = clean_name(name_blob).casefold()

            team_blob = " ".join(
                str(player.get(field) or "")
                for field in ["strTeam", "strTeam2", "strNationality"]
            ).casefold()

            score = 0
            if wanted and wanted in name_blob_clean:
                score += 5
            if team_wanted and team_wanted in team_blob:
                score += 2
            if player.get("strThumb") or player.get("strCutout"):
                score += 1

            candidates.append((score, player))

        candidates.sort(key=lambda item: item[0], reverse=True)
        if not candidates or candidates[0][0] <= 0:
            return players[0] if players else None

        return candidates[0][1]

    def _normalise_player(self, raw: dict, fallback_name: str) -> dict:
        photo = (
            raw.get("strCutout")
            or raw.get("strRender")
            or raw.get("strThumb")
            or raw.get("strFanart1")
        )

        return {
            "id": raw.get("idPlayer"),
            "name": raw.get("strPlayer") or fallback_name,
            "age": None,
            "number": raw.get("strNumber"),
            "position": raw.get("strPosition") or "Player",
            "photo": photo,
            "rating": None,
            "nationality": raw.get("strNationality"),
            "provider_team": raw.get("strTeam"),
        }

    def roster(self, team_name: str) -> dict:
        names = TEAM_PLAYER_SEEDS.get(team_name)

        if not names:
            raise TheSportsDBError(f"No TheSportsDB seed player list exists for {team_name} yet.")

        players = []
        errors = []

        for name in names:
            try:
                payload = self._search_player(name)
                raw = self._pick_player(name, team_name, payload or {})
                if raw:
                    players.append(self._normalise_player(raw, name))
            except Exception as error:
                errors.append(f"{name}: {error}")

        if not players:
            raise TheSportsDBError(
                "No usable TheSportsDB players were found. "
                + ("; ".join(errors[:3]) if errors else "")
            )

        return {
            "team": team_name,
            "provider": "TheSportsDB",
            "provider_team": team_name,
            "players": players,
            "cached": True,
            "rating_note": "This player snapshot is loaded from TheSportsDB search results. It is used for visual context only and does not change the Elo + Poisson prediction model.",
            "provider_warning": "TheSportsDB fallback uses seeded player-name searches, so it may not be a full official squad.",
        }
