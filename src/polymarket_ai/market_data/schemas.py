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
    token_id: str | None = None


class MarketRules(BaseModel):
    raw_rules: str
    parsed_resolution_criteria: list[str]
    source_url: HttpUrl | None = None
    source_name: str | None = None


class NormalizedMarket(BaseModel):
    venue: str = "kalshi"
    event_id: str
    market_id: str
    question: str
    category: str
    series_id: str | None = None
    slug: str | None = None
    condition_id: str | None = None
    event_slug: str | None = None
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
    spread: float | None = None
    clob_token_ids: list[str] = Field(default_factory=list)
    recent_trade_count: int = 0
    recent_trade_volume: float = 0.0
    recent_buy_volume: float = 0.0
    recent_sell_volume: float = 0.0
    last_activity_at: datetime | None = None
    attention_score: float = Field(default=0.0, ge=0.0, le=1.0)


class MarketSnapshot(BaseModel):
    as_of: datetime
    source: str
    markets: list[NormalizedMarket]
