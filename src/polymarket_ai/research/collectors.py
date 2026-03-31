from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from polymarket_ai.market_data.schemas import NormalizedMarket
from polymarket_ai.research.schemas import (
    EvidenceDirection,
    ExtractedClaim,
    ResearchPacket,
    ResearchSource,
    SourceQuality,
)


class SearchClient:
    def search(self, query: str) -> list[ResearchSource]:
        raise NotImplementedError("Plug web search or custom provider here.")


class ResearchCollector(Protocol):
    def collect(self, market: NormalizedMarket) -> list[ResearchSource]:
        ...


class ResearchSynthesizerProtocol(Protocol):
    def build_packet(self, market: NormalizedMarket, sources: list[ResearchSource]) -> ResearchPacket:
        ...


@dataclass(slots=True)
class StaticResearchCollector:
    """Useful for local examples and tests."""

    def collect(self, market: NormalizedMarket) -> list[ResearchSource]:
        return [
            ResearchSource(
                title="NOAA seasonal outlook",
                url="https://www.noaa.gov/",
                publisher="NOAA",
                published_at=date(2026, 3, 1),
                excerpt="Official outlook points to elevated hurricane activity.",
                quality=SourceQuality.HIGH,
                direction=EvidenceDirection.SUPPORTS,
                is_official=True,
            ),
            ResearchSource(
                title="Academic historical baseline study",
                url="https://example.org/hurricane-study",
                publisher="Example Journal",
                published_at=date(2025, 11, 10),
                excerpt="Historical baseline suggests tail risk but still moderate central estimate.",
                quality=SourceQuality.MEDIUM,
                direction=EvidenceDirection.OPPOSES,
                is_official=False,
            ),
        ]


class ResearchSynthesizer:
    def build_packet(self, market: NormalizedMarket, sources: list[ResearchSource]) -> ResearchPacket:
        supporting = [
            ExtractedClaim(
                claim="Official NOAA guidance indicates elevated hurricane activity.",
                direction=EvidenceDirection.SUPPORTS,
                numeric_fact="Above-average activity expected",
                date_reference=date(2026, 3, 1),
                source_title=sources[0].title,
                weight=0.70,
                uncertainty_note="Seasonal forecasts remain probabilistic.",
            )
        ]
        opposing = [
            ExtractedClaim(
                claim="Historical baselines can overstate extreme-year probabilities if current conditions normalize.",
                direction=EvidenceDirection.OPPOSES,
                numeric_fact="Long-run base rate remains lower than worst-case scenario",
                date_reference=date(2025, 11, 10),
                source_title=sources[-1].title,
                weight=0.45,
                uncertainty_note="Backward-looking studies may miss current-cycle conditions.",
            )
        ]
        return ResearchPacket(
            market_id=market.market_id,
            question=market.question,
            rules_summary=market.rules.parsed_resolution_criteria,
            supporting_claims=supporting,
            opposing_claims=opposing,
            source_summaries=sources,
            source_quality_score=0.75,
            evidence_freshness_score=0.80,
            crowd_might_be_wrong=[
                "General attention may be focused on headline politics rather than this niche seasonal market.",
                "Rule wording rewards precise interpretation of what counts toward resolution.",
            ],
            we_might_be_wrong=[
                "Seasonal outlooks can shift materially as new weather data arrives.",
                "The market may already incorporate private or expert views not visible in public sources.",
            ],
            rule_risk_notes=[
                "Recommendation should be blocked if the official counting methodology becomes ambiguous.",
            ],
        )
