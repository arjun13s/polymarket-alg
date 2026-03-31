from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from polymarket_ai.models.domain import Market, ProbabilityEstimate, ResearchReport, TradeDecision


class AgentModelConfig(BaseModel):
    model_name: str
    max_retries: int = 2
    timeout_seconds: int = 30


class ToolCallRecord(BaseModel):
    tool_name: str
    status: str
    started_at: datetime
    ended_at: datetime
    details: str


class AgentTrace(BaseModel):
    trace_id: str
    agent_name: str
    instructions: str
    model_config: AgentModelConfig
    reasoning_steps: list[str]
    tool_calls: list[ToolCallRecord]
    started_at: datetime
    ended_at: datetime


class RulesAgentInput(BaseModel):
    trace_id: str
    market: Market
    outcome_id: str


class RulesAgentOutput(BaseModel):
    parsed_rules: list[str]
    ambiguity_flags: list[str]
    rule_clarity_score: float = Field(ge=0.0, le=1.0)
    recommendation_notes: list[str]
    trace: AgentTrace


class ResearchAgentInput(BaseModel):
    trace_id: str
    market: Market
    outcome_id: str
    rules_output: RulesAgentOutput


class ResearchAgentOutput(BaseModel):
    report: ResearchReport
    trace: AgentTrace


class SkepticAgentInput(BaseModel):
    trace_id: str
    market: Market
    research_output: ResearchAgentOutput
    rules_output: RulesAgentOutput


class SkepticAgentOutput(BaseModel):
    skepticism_score: float = Field(ge=0.0, le=1.0)
    why_crowd_might_be_wrong: list[str]
    why_we_might_be_wrong: list[str]
    trace: AgentTrace


class ProbabilityAgentInput(BaseModel):
    trace_id: str
    market: Market
    outcome_id: str
    rules_output: RulesAgentOutput
    research_output: ResearchAgentOutput
    skeptic_output: SkepticAgentOutput


class ProbabilityAgentOutput(BaseModel):
    fair_prob: float = Field(ge=0.0, le=1.0)
    lower_bound: float = Field(ge=0.0, le=1.0)
    upper_bound: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str
    trace: AgentTrace


class OrchestratorDecisionEnvelope(BaseModel):
    trace_id: str
    market: Market
    rules: RulesAgentOutput
    research: ResearchAgentOutput
    skeptic: SkepticAgentOutput
    probability: ProbabilityAgentOutput
    probability_estimate: ProbabilityEstimate
    decision: TradeDecision

