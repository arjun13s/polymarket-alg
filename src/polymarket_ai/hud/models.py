from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DecisionKind(str, Enum):
    NO_TRADE = "NO_TRADE"
    WATCHLIST = "WATCHLIST"
    PAPER_TRADE = "PAPER_TRADE"


class ToolRunInput(BaseModel):
    market_id: str
    trace_id: str
    run_id: str | None = None


class ToolRunOutput(BaseModel):
    tool_name: str
    trace_id: str
    started_at: datetime
    finished_at: datetime
    output: dict[str, object]


class RuleAnalysis(BaseModel):
    market_id: str
    parsed_rules: list[str]
    risks: list[str]
    clarity_score: float = Field(ge=0.0, le=1.0)
    trace: dict[str, object] | None = None


class ResearchOutput(BaseModel):
    market_id: str
    summary: str
    sources: list[str]
    supporting_points: list[str]
    opposing_points: list[str]
    risks: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    trace: dict[str, object] | None = None


class SkepticOutput(BaseModel):
    market_id: str
    counter_arguments: list[str]
    failure_modes: list[str]
    confidence_penalty: float = Field(ge=0.0, le=1.0)
    trace: dict[str, object] | None = None


class ProbabilityOutput(BaseModel):
    market_id: str
    market_prob: float = Field(ge=0.0, le=1.0)
    fair_prob: float = Field(ge=0.0, le=1.0)
    edge: float
    confidence: float = Field(ge=0.0, le=1.0)
    expected_value: float
    decision: DecisionKind
    reasoning_summary: str
    risks: list[str]
    sources: list[str]
    trace: dict[str, object] | None = None


class FinalDecision(BaseModel):
    market_id: str
    market_prob: float = Field(ge=0.0, le=1.0)
    fair_prob: float = Field(ge=0.0, le=1.0)
    edge: float
    confidence: float = Field(ge=0.0, le=1.0)
    decision: DecisionKind
    reasoning_summary: str
    risks: list[str]
    sources: list[str]
    expected_value: float
    run_id: str
    trace_id: str
    snapshot_as_of: datetime | None = None
    agent_outputs: dict[str, object] | None = None


class ScenarioResult(BaseModel):
    name: str
    output: dict[str, object]
    score: float = Field(ge=0.0, le=1.0)
    notes: list[str]
    component_scores: dict[str, float] = Field(default_factory=dict)
