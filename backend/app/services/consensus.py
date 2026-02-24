from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from backend.app.services.odds_math import american_to_implied_prob, remove_vig_two_way


@dataclass
class ConsensusResult:
    home_prob: float
    away_prob: float


def build_market_consensus(lines: list[dict]) -> ConsensusResult:
    by_book: dict[str, dict[str, float]] = defaultdict(dict)
    for row in lines:
        by_book[row['book']][row['side']] = american_to_implied_prob(row['price'])

    home_probs: list[float] = []
    away_probs: list[float] = []
    for _, two_way in by_book.items():
        if 'home' not in two_way or 'away' not in two_way:
            continue
        home, away = remove_vig_two_way(two_way['home'], two_way['away'])
        home_probs.append(home)
        away_probs.append(away)

    return ConsensusResult(home_prob=sum(home_probs) / len(home_probs), away_prob=sum(away_probs) / len(away_probs))
