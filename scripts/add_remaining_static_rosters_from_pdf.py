#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    raise SystemExit("Missing dependency. Run: python3 -m pip install pymupdf")


PDF_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("2026 FIFA World Cup squads - Wikipedia.pdf")
OUT_PATH = Path("backend/static_rosters.json")

TARGET_TEAMS = {
    "Switzerland",
    "Morocco",
    "United States",
    "Paraguay",
    "Australia",
    "Germany",
    "Belgium",
}

TEAM_ORDER = [
    "Czech Republic", "Mexico", "South Africa", "South Korea",
    "Bosnia and Herzegovina", "Canada", "Qatar", "Switzerland",
    "Brazil", "Haiti", "Morocco", "Scotland",
    "Australia", "Paraguay", "Turkey", "United States",
    "Curaçao", "Ecuador", "Germany", "Ivory Coast",
    "Japan", "Netherlands", "Sweden", "Tunisia",
    "Belgium", "Egypt", "Iran", "New Zealand",
    "Cape Verde", "Saudi Arabia", "Spain", "Uruguay",
    "France", "Iraq", "Norway", "Senegal",
    "Algeria", "Argentina", "Austria", "Jordan",
    "Colombia", "DR Congo", "Portugal", "Uzbekistan",
    "Croatia", "England", "Ghana", "Panama",
]

POS_MAP = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "FW": "Forward",
}


def p(number: int, name: str, position: str) -> dict:
    return {
        "id": None,
        "name": name,
        "age": None,
        "number": number,
        "position": position,
        "photo": None,
        "rating": None,
        "source": "pdf-static-roster",
    }


def team_payload(team_name: str, players: list[dict]) -> dict:
    return {
        "team": team_name,
        "provider": "PDF static roster snapshot",
        "cached": True,
        "players": players,
        "rating_note": (
            "This is a static roster snapshot extracted from the uploaded 2026 FIFA World Cup squads PDF. "
            "It is used for visual roster context only and does not affect the prediction model."
        ),
    }


def is_footer(line: str) -> bool:
    line = line.strip()
    return (
        not line
        or re.match(r"^\d+/\d+/\d+,", line)
        or line.startswith("2026 FIFA World Cup squads")
        or line.startswith("https://")
        or re.match(r"^\d+/119$", line)
    )


def line_index_for_char(line_starts: list[int], pos: int) -> int:
    lo, hi = 0, len(line_starts)
    while lo < hi:
        mid = (lo + hi) // 2
        if line_starts[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


def parse_team(text: str, lines: list[str], line_starts: list[int], team_name: str, next_team: str | None) -> list[dict]:
    idx = text.find(f"\n{team_name}\n")
    if idx == -1:
        raise ValueError(f"Could not find section for {team_name}")

    start_li = line_index_for_char(line_starts, idx) + 1

    if next_team:
        end_idx = text.find(f"\n{next_team}\n", idx + 1)
        end_li = line_index_for_char(line_starts, end_idx) + 1 if end_idx != -1 else len(lines)
    else:
        end_li = len(lines)

    section_lines = [line.strip() for line in lines[start_li:end_li]]

    players = []
    i = 0
    while i < len(section_lines) - 2:
        current = section_lines[i].strip()

        if current.isdigit() and 1 <= int(current) <= 26:
            number = int(current)

            j = i + 1
            while j < len(section_lines) and is_footer(section_lines[j]):
                j += 1

            if j < len(section_lines) and section_lines[j] in POS_MAP:
                position = POS_MAP[section_lines[j]]

                k = j + 1
                while k < len(section_lines) and is_footer(section_lines[k]):
                    k += 1

                name_parts = []
                while k < len(section_lines):
                    line = section_lines[k].strip()

                    if is_footer(line):
                        k += 1
                        continue

                    if re.match(r"^\d{1,2} [A-Z][a-z]+", line) or re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}", line):
                        break

                    if line.isdigit() and k + 1 < len(section_lines) and section_lines[k + 1] in POS_MAP:
                        break

                    name_parts.append(line)
                    k += 1

                    if len(name_parts) > 3:
                        break

                name = " ".join(name_parts).strip()
                name = re.sub(r"\s*\(captain\)", "", name).strip()

                if name:
                    players.append(p(number, name, position))

                i = k
                continue

        i += 1

    by_number = {}
    for player in players:
        by_number[player["number"]] = player

    return [by_number[number] for number in sorted(by_number)]


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(f"Could not find PDF: {PDF_PATH}")

    doc = fitz.open(PDF_PATH)
    text = "\n".join(page.get_text() for page in doc)
    lines = text.splitlines()

    line_starts = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1

    data = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else {}

    added = []
    for team_name in TARGET_TEAMS:
        team_index = TEAM_ORDER.index(team_name)
        next_team = TEAM_ORDER[team_index + 1] if team_index + 1 < len(TEAM_ORDER) else None

        players = parse_team(text, lines, line_starts, team_name, next_team)

        if len(players) != 26:
            raise SystemExit(f"{team_name}: expected 26 players, got {len(players)}")

        data[team_name] = team_payload(team_name, players)
        added.append(team_name)

    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print(f"Added/updated {len(added)} teams:")
    for team_name in sorted(added):
        print(f"✅ {team_name}: {len(data[team_name]['players'])} players")

    print(f"Total static teams now: {len(data)}")


if __name__ == "__main__":
    main()
