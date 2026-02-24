"""Odds and sizing math utilities."""

from __future__ import annotations


def american_to_decimal(american: int) -> float:
    if american > 0:
        return (american / 100) + 1
    return (100 / abs(american)) + 1


def decimal_to_implied_prob(decimal_odds: float) -> float:
    return 1 / decimal_odds


def american_to_implied_prob(american: int) -> float:
    return decimal_to_implied_prob(american_to_decimal(american))


def remove_vig_two_way(prob_a: float, prob_b: float) -> tuple[float, float]:
    total = prob_a + prob_b
    return prob_a / total, prob_b / total


def ev_percent(model_probability: float, decimal_odds: float) -> float:
    return (model_probability * decimal_odds) - 1


def full_kelly(p: float, decimal_odds: float) -> float:
    return (p * decimal_odds - 1) / (decimal_odds - 1)


def quarter_kelly(p: float, decimal_odds: float) -> float:
    return max(0.0, full_kelly(p, decimal_odds) * 0.25)
