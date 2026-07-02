#!/usr/bin/env python3
"""Export clean static roster snapshots from the local app/API-Football cache.

This calls the local FastAPI endpoint so we export the normalized app shape,
not the raw provider cache.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path


TEAMS = [
    "Mexico", "South Africa", "South Korea", "Czechia",
    "Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland",
    "Brazil", "Morocco", "Haiti", "Scotland",
    "United States", "Paraguay", "Australia", "Turkey",
    "Germany", "Curacao", "Ivory Coast", "Ecuador",
    "Netherlands", "Japan", "Sweden", "Tunisia",
    "Belgium", "Egypt", "Iran", "New Zealand",
    "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
    "France", "Senegal", "Iraq", "Norway",
    "Argentina", "Algeria", "Austria", "Jordan",
    "Portugal", "DR Congo", "Uzbekistan", "Colombia",
    "England", "Croatia", "Ghana", "Panama",
]

BASE_URL = "http://127.0.0.1:8001/api/team-roster"
OUT_PATH = Path("backend/static_rosters.json")


def fetch(team: str) -> dict:
    url = f"{BASE_URL}?team={urllib.parse.quote(team)}&provider=api_football"
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_player(player: dict) -> dict:
    return {
        "id": player.get("id"),
        "name": player.get("name"),
        "age": player.get("age"),
        "number": player.get("number"),
        "position": player.get("position"),
        "photo": player.get("photo"),
        "rating": None,
    }


def main() -> None:
    exported = {}
    missing = {}

    for team in TEAMS:
        try:
            payload = fetch(team)
            players = payload.get("players") or []

            if payload.get("cached") is True and len(players) >= 5:
                exported[team] = {
                    "team": team,
                    "provider": "Static API-Football cache",
                    "provider_team": payload.get("provider_team") or team,
                    "players": [clean_player(player) for player in players if player.get("name")],
                    "cached": True,
                    "rating_note": (
                        "This is a static roster snapshot exported from local API-Football cache. "
                        "It is used for visual roster context only and does not affect the prediction model."
                    ),
                }
                print(f"✅ {team}: {len(players)} players")
            else:
                missing[team] = {
                    "reason": "not cached or too few players",
                    "provider": payload.get("provider"),
                    "cached": payload.get("cached"),
                    "players": len(players),
                    "detail": payload.get("detail"),
                }
                print(f"❌ {team}: not cached")

        except Exception as error:
            missing[team] = {"reason": str(error)}
            print(f"❌ {team}: {error}")

    OUT_PATH.write_text(json.dumps(exported, indent=2, ensure_ascii=False) + "\n")

    print()
    print(f"Exported teams: {len(exported)}")
    print(f"Missing teams: {len(missing)}")
    print(f"Wrote: {OUT_PATH}")

    if missing:
        print()
        print("Missing:")
        for team in missing:
            print("-", team)


if __name__ == "__main__":
    main()
