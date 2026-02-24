from __future__ import annotations

from datetime import datetime


def build_pregame_features(event_id: int, as_of: datetime) -> dict:
    """Baseline feature structure for NBA pre-game modeling."""
    return {
        "event_id": event_id,
        "team_win_loss_home_away": 0.52,
        "recent_form_last_n": 0.5,
        "head_to_head": 0.5,
        "rest_days_density": 0.0,
        "off_def_efficiency": 0.0,
        "home_court_advantage": 1.0,
        "as_of": as_of.isoformat(),
    }
