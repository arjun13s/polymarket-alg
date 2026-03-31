from __future__ import annotations

from pydantic import BaseModel

from polymarket_ai.pricing.schemas import ProbabilityEstimate
from polymarket_ai.research.schemas import ResearchPacket


class WorkflowStepLog(BaseModel):
    step_name: str
    status: str
    summary: str


class FinalMemo(BaseModel):
    market_id: str
    outcome_id: str
    recommendation: str
    confidence: float
    why_crowd_might_be_wrong: list[str]
    why_we_might_be_wrong: list[str]
    resolution_rule_check: list[str]
    source_quality_notes: list[str]
    research: ResearchPacket
    pricing: ProbabilityEstimate
    step_logs: list[WorkflowStepLog]
