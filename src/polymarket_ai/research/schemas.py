from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceDirection(str, Enum):
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    UNCLEAR = "unclear"


class ResearchSource(BaseModel):
    title: str
    url: HttpUrl
    publisher: str
    published_at: date | None = None
    excerpt: str
    quality: SourceQuality
    direction: EvidenceDirection
    is_official: bool = False


class ExtractedClaim(BaseModel):
    claim: str
    direction: EvidenceDirection
    numeric_fact: str | None = None
    date_reference: date | None = None
    source_title: str
    weight: float = Field(ge=0.0, le=1.0)
    uncertainty_note: str


class ResearchPacket(BaseModel):
    market_id: str
    question: str
    rules_summary: list[str]
    supporting_claims: list[ExtractedClaim]
    opposing_claims: list[ExtractedClaim]
    source_summaries: list[ResearchSource]
    source_quality_score: float = Field(ge=0.0, le=1.0)
    evidence_freshness_score: float = Field(ge=0.0, le=1.0)
    crowd_might_be_wrong: list[str]
    we_might_be_wrong: list[str]
    rule_risk_notes: list[str]
