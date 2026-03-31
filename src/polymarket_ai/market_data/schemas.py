from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


class OutcomeQuote(BaseModel):
    outcome_id: str
    name: str
    price: float = Field(ge=0.0, le=1.0)
    implied_probability: float = Field(ge=0.0, le=1.0)


class MarketRules(BaseModel):
    raw_rules: str
    parsed_resolution_criteria: list[str]
    source_url: HttpUrl | None = None


class NormalizedMarket(BaseModel):
    event_id: str
    market_id: str
    question: str
    category: str
    end_date: datetime | None = None
    status: MarketStatus
    liquidity: float = 0.0
    volume_24h: float = 0.0
    volume_total: float = 0.0
    description: str | None = None
    rules: MarketRules
    outcomes: list[OutcomeQuote]
    best_bid: float | None = None
    best_ask: float | None = None
    last_price: float | None = None
    attention_score: float = Field(default=0.0, ge=0.0, le=1.0)


class MarketSnapshot(BaseModel):
    as_of: datetime
    source: str
    markets: list[NormalizedMarket]
