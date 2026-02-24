from backend.app.services.consensus import build_market_consensus


def test_vig_removal_consensus() -> None:
    lines = [
        {"book": "a", "side": "home", "price": -110},
        {"book": "a", "side": "away", "price": +100},
        {"book": "b", "side": "home", "price": -105},
        {"book": "b", "side": "away", "price": -105},
    ]
    result = build_market_consensus(lines)
    assert 0.49 < result.home_prob < 0.53
    assert round(result.home_prob + result.away_prob, 6) == 1.0
