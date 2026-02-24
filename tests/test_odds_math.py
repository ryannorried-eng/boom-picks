from backend.app.services.odds_math import (
    american_to_decimal,
    american_to_implied_prob,
    decimal_to_implied_prob,
    ev_percent,
    quarter_kelly,
)


def test_odds_conversions() -> None:
    assert round(american_to_decimal(+150), 3) == 2.5
    assert round(american_to_decimal(-110), 3) == 1.909
    assert round(decimal_to_implied_prob(2.5), 3) == 0.4
    assert round(american_to_implied_prob(-110), 3) == 0.524


def test_ev_and_kelly_exact() -> None:
    p = 0.55
    odds = 1.91
    assert round(ev_percent(p, odds), 4) == 0.0505
    assert round(quarter_kelly(p, odds), 4) == round((((p * odds) - 1) / (odds - 1)) * 0.25, 4)
