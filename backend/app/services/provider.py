from __future__ import annotations

from datetime import datetime, timedelta


class MockOddsProvider:
    async def fetch_events_and_odds(self) -> list[dict]:
        start = datetime.utcnow() + timedelta(minutes=5)
        return [
            {
                "source": "mock",
                "external_event_id": "evt-1",
                "league": "NBA",
                "start_time": start,
                "home_team": "los angeles lakers",
                "away_team": "golden state warriors",
                "odds": [
                    {"book": "book_a", "market": "moneyline", "side": "home", "price": -110, "timestamp": datetime.utcnow()},
                    {"book": "book_a", "market": "moneyline", "side": "away", "price": +100, "timestamp": datetime.utcnow()},
                    {"book": "book_b", "market": "moneyline", "side": "home", "price": -105, "timestamp": datetime.utcnow()},
                    {"book": "book_b", "market": "moneyline", "side": "away", "price": -105, "timestamp": datetime.utcnow()},
                ],
            }
        ]


class DeterministicMockOddsProvider:
    """Test-only provider that guarantees at least one eligible pick."""

    async def fetch_events_and_odds(self) -> list[dict]:
        now = datetime.utcnow()
        start = now + timedelta(minutes=5)
        line_ts = now - timedelta(seconds=15)
        return [
            {
                "source": "deterministic-mock",
                "external_event_id": "evt-deterministic-1",
                "league": "NBA",
                "start_time": start,
                "home_team": "los angeles lakers",
                "away_team": "golden state warriors",
                "odds": [
                    {"book": "book_a", "market": "moneyline", "side": "home", "price": -110, "timestamp": line_ts},
                    {"book": "book_a", "market": "moneyline", "side": "away", "price": +100, "timestamp": line_ts},
                    {"book": "book_b", "market": "moneyline", "side": "home", "price": -108, "timestamp": line_ts},
                    {"book": "book_b", "market": "moneyline", "side": "away", "price": -102, "timestamp": line_ts},
                    {"book": "book_c", "market": "moneyline", "side": "home", "price": -105, "timestamp": line_ts},
                    {"book": "book_c", "market": "moneyline", "side": "away", "price": -105, "timestamp": line_ts},
                ],
            }
        ]
