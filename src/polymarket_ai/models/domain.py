from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from polymarket_ai.market_data.schemas import NormalizedMarket
from polymarket_ai.research.schemas import ResearchSource


class Market(NormalizedMarket):
    """Application-facing market model."""


class ResearchReport(BaseModel):
    run_id: str | None = None
    market_id: str
    outcome_id: str | None = None
    question: str | None = None
    rules_summary: list[str] = Field(default_factory=list)
    source_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_evidence: list[str] = Field(default_factory=list)
    opposing_evidence: list[str] = Field(default_factory=list)
    crowd_might_be_wrong: list[str] = Field(default_factory=list)
    skeptical_risks: list[str] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(default_factory=list)
    summary: str = ""
    source_summary: list[ResearchSource] = Field(default_factory=list)
    supporting_claims: list[str] = Field(default_factory=list)
    opposing_claims: list[str] = Field(default_factory=list)
    why_crowd_might_be_wrong: list[str] = Field(default_factory=list)
    why_we_might_be_wrong: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ProbabilityEstimate(BaseModel):
    market_id: str
    outcome_id: str
    market_prob: float = Field(ge=0.0, le=1.0)
    fair_prob: float = Field(ge=0.0, le=1.0)
    lower_bound: float = Field(ge=0.0, le=1.0)
    upper_bound: float = Field(ge=0.0, le=1.0)
    edge: float = Field(ge=-1.0, le=1.0)
    expected_value: float
    confidence: float = Field(ge=0.0, le=1.0)
    executable_price: float = Field(ge=0.0, le=1.0)
    cost: float = Field(ge=0.0, le=1.0)
    tradeable: bool
    reject_reason: str | None = None
    reasoning_summary: str


class TradeDecision(BaseModel):
    market_id: str
    market_prob: float = Field(ge=0.0, le=1.0)
    fair_prob: float = Field(ge=0.0, le=1.0)
    edge: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    decision: str
    reasoning_summary: str
    risks: list[str]
    sources: list[str]
    expected_value: float
    outcome_id: str | None = None
    trace_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    run_id: str | None = None
    snapshot_at: datetime | None = None


class ProbabilityEstimateView(BaseModel):
    market_id: str
    fair_prob: float = Field(ge=0.0, le=1.0)
    market_prob: float = Field(ge=0.0, le=1.0)
    edge: float
    confidence: float = Field(ge=0.0, le=1.0)
    expected_value: float
    decision: str
    reasoning_summary: str
    risks: list[str]
    sources: list[str]


class RuleAnalysis(BaseModel):
    market_id: str
    parsed_rules: list[str]
    risks: list[str]
    clarity_score: float = Field(ge=0.0, le=1.0)


class SkepticAssessment(BaseModel):
    market_id: str
    failure_modes: list[str]
    confidence_penalty: float = Field(ge=0.0, le=1.0)


class RunRecord(BaseModel):
    run_id: str
    market_id: str
    inputs: dict[str, object]
    agent_outputs: dict[str, object]
    final_decision: TradeDecision
    started_at: datetime
    finished_at: datetime
    trace_id: str
