from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.services.odds_math import american_to_implied_prob, remove_vig_two_way


@dataclass
class ConsensusResult:
    home_prob: float
    away_prob: float
    books_used: int


@dataclass
class ConsensusDecision:
    result: ConsensusResult | None
    missing_reason: str | None = None


def _trim_outliers(values: list[float], enabled: bool) -> list[float]:
    """Trim one low/high value for sufficiently deep books."""
    if not enabled or len(values) < 6:
        return values
    ordered = sorted(values)
    return ordered[1:-1]


def build_market_consensus(lines: list[dict], *, min_books: int | None = None, book_weights: dict[str, float] | None = None) -> ConsensusDecision:
    """Build market consensus with guardrails for stale/missing/outlier inputs."""
    threshold = min_books or settings.consensus_min_books
    by_book: dict[str, dict[str, float]] = defaultdict(dict)
    for row in lines:
        if row.get("is_stale"):
            continue
        by_book[row["book"]][row["side"]] = american_to_implied_prob(row["price"])

    if len(by_book) < threshold:
        return ConsensusDecision(result=None, missing_reason="INSUFFICIENT_BOOKS")

    home_probs: list[float] = []
    away_probs: list[float] = []
    usable_books: list[str] = []
    for book, two_way in by_book.items():
        if "home" not in two_way or "away" not in two_way:
            continue
        home, away = remove_vig_two_way(two_way["home"], two_way["away"])
        home_probs.append(home)
        away_probs.append(away)
        usable_books.append(book)

    if len(home_probs) < threshold:
        return ConsensusDecision(result=None, missing_reason="INCOMPLETE_TWO_WAY_MARKET")

    home_probs = _trim_outliers(home_probs, settings.consensus_trim_outliers)
    away_probs = _trim_outliers(away_probs, settings.consensus_trim_outliers)

    # Explicit weighting support (default equal weights).
    weights = [float((book_weights or {}).get(book, 1.0)) for book in usable_books[: len(home_probs)]]
    weight_sum = sum(weights)
    if weight_sum <= 0:
        return ConsensusDecision(result=None, missing_reason="INVALID_BOOK_WEIGHTS")

    home_consensus = sum(p * w for p, w in zip(home_probs, weights, strict=False)) / weight_sum
    away_consensus = sum(p * w for p, w in zip(away_probs, weights, strict=False)) / weight_sum
    return ConsensusDecision(result=ConsensusResult(home_prob=home_consensus, away_prob=away_consensus, books_used=len(home_probs)))
