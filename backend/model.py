"""A transparent Elo + Poisson football prediction model."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from .data import Fixture


BASE_ELO = 1500.0
HOME_ADVANTAGE = 55.0
K_FACTOR = 24.0


@dataclass
class Prediction:
    home: str
    away: str
    home_win: float
    draw: float
    away_win: float
    expected_home_goals: float
    expected_away_goals: float
    scoreline: str
    confidence: str
    factors: list[str]

    def as_dict(self) -> dict:
        return {
            "home": self.home,
            "away": self.away,
            "home_win": round(self.home_win * 100, 1),
            "draw": round(self.draw * 100, 1),
            "away_win": round(self.away_win * 100, 1),
            "expected_home_goals": round(self.expected_home_goals, 2),
            "expected_away_goals": round(self.expected_away_goals, 2),
            "scoreline": self.scoreline,
            "confidence": self.confidence,
            "factors": self.factors,
        }


class EloPoissonEngine:
    def __init__(self, fixtures: list[Fixture]):
        self.fixtures = fixtures
        self.ratings: dict[str, float] = defaultdict(lambda: BASE_ELO)
        self.attack: dict[str, float] = defaultdict(lambda: 1.0)
        self.defence: dict[str, float] = defaultdict(lambda: 1.0)
        self._train()

    def _train(self) -> None:
        goals_for: dict[str, int] = defaultdict(int)
        goals_against: dict[str, int] = defaultdict(int)
        appearances: dict[str, int] = defaultdict(int)
        for fixture in self.fixtures:
            if not fixture.complete:
                continue
            home, away = fixture.home, fixture.away
            hg, ag = fixture.home_goals or 0, fixture.away_goals or 0
            home_expected = 1 / (1 + 10 ** (-((self.ratings[home] + HOME_ADVANTAGE - self.ratings[away]) / 400)))
            actual = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
            change = K_FACTOR * (actual - home_expected)
            self.ratings[home] += change
            self.ratings[away] -= change
            goals_for[home] += hg; goals_against[home] += ag; appearances[home] += 1
            goals_for[away] += ag; goals_against[away] += hg; appearances[away] += 1
        global_avg = sum(goals_for.values()) / max(sum(appearances.values()), 1)
        global_avg = max(global_avg, 1.0)
        for team, games in appearances.items():
            # Light smoothing stops a small historical sample becoming overconfident.
            self.attack[team] = (goals_for[team] + global_avg * 3) / ((games + 3) * global_avg)
            self.defence[team] = (goals_against[team] + global_avg * 3) / ((games + 3) * global_avg)

    @staticmethod
    def _poisson(k: int, rate: float) -> float:
        return math.exp(-rate) * rate**k / math.factorial(k)

    def predict(self, home: str, away: str) -> Prediction:
        elo_diff = self.ratings[home] + HOME_ADVANTAGE - self.ratings[away]
        elo_home = 1 / (1 + 10 ** (-elo_diff / 400))
        home_xg = max(0.35, 1.30 * self.attack[home] * self.defence[away] * (0.82 + elo_home * 0.36))
        away_xg = max(0.25, 1.15 * self.attack[away] * self.defence[home] * (1.18 - elo_home * 0.36))
        home_win = draw = away_win = 0.0
        best = (0, 0, 0.0)
        for h in range(7):
            for a in range(7):
                probability = self._poisson(h, home_xg) * self._poisson(a, away_xg)
                if h > a: home_win += probability
                elif h == a: draw += probability
                else: away_win += probability
                if probability > best[2]: best = (h, a, probability)
        total = home_win + draw + away_win
        home_win, draw, away_win = home_win / total, draw / total, away_win / total
        margin = max(home_win, away_win) - min(home_win, away_win)
        confidence = "High" if margin > 0.29 else "Medium" if margin > 0.12 else "Low"
        stronger = home if elo_diff >= 0 else away
        factors = [
            f"{stronger} Elo edge: {abs(elo_diff):.0f} points",
            f"Expected goals: {home_xg:.2f}–{away_xg:.2f}",
            f"{home} attack index {self.attack[home]:.2f}; {away} defence index {self.defence[away]:.2f}",
        ]
        return Prediction(home, away, home_win, draw, away_win, home_xg, away_xg, f"{best[0]}–{best[1]}", confidence, factors)

    def standings(self, group: str) -> list[dict]:
        table: dict[str, dict] = {}
        for fixture in self.fixtures:
            if fixture.group != group:
                continue
            for team in (fixture.home, fixture.away):
                table.setdefault(team, {"team": team, "played": 0, "points": 0, "goal_difference": 0})
            if not fixture.complete:
                continue
            home, away = table[fixture.home], table[fixture.away]
            hg, ag = fixture.home_goals or 0, fixture.away_goals or 0
            home["played"] += 1; away["played"] += 1
            home["goal_difference"] += hg - ag; away["goal_difference"] += ag - hg
            if hg > ag: home["points"] += 3
            elif ag > hg: away["points"] += 3
            else: home["points"] += 1; away["points"] += 1
        return sorted(table.values(), key=lambda row: (row["points"], row["goal_difference"]), reverse=True)
