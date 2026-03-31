from __future__ import annotations

from pydantic import BaseModel, Field


class ProbabilityEstimate(BaseModel):
    outcome_id: str
    executable_price: float = Field(ge=0.0, le=1.0)
    fee_and_slippage_cost: float = Field(ge=0.0, le=1.0)
    market_probability: float = Field(ge=0.0, le=1.0)
    fair_probability: float = Field(ge=0.0, le=1.0)
    lower_bound: float = Field(ge=0.0, le=1.0)
    upper_bound: float = Field(ge=0.0, le=1.0)
    edge: float = Field(ge=-1.0, le=1.0)
    expected_value: float
    downside_expected_value: float
    uncertainty_width: float = Field(ge=0.0, le=1.0)
    tradeable: bool
    no_trade_reason: str | None = None
    rationale: str
