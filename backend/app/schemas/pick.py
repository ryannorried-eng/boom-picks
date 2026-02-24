from datetime import datetime

from pydantic import BaseModel


class PickOut(BaseModel):
    id: int
    pick_lifecycle_id: str
    market: str
    side: str
    book: str
    model_prob: float
    market_consensus_prob: float
    model_edge: float
    ev_percent: float
    kelly_fraction: float
    tier: str
    created_at: datetime
