from __future__ import annotations

from polymarket_ai.models import Market, ResearchReport, RuleAnalysis, SkepticAssessment
from polymarket_ai.research.collectors import ResearchCollector, ResearchSynthesizer, StaticResearchCollector
from polymarket_ai.services.market_service import MarketService
from polymarket_ai.repositories.research_repo import ResearchRepository


class ResearchService:
    def __init__(
        self,
        market_service: MarketService,
        research_repo: ResearchRepository,
        collector: ResearchCollector | None = None,
        synthesizer: ResearchSynthesizer | None = None,
    ) -> None:
        self._market_service = market_service
        self._research_repo = research_repo
        self._collector = collector or StaticResearchCollector()
        self._synthesizer = synthesizer or ResearchSynthesizer()

    def search_web(self, market: Market) -> list[str]:
        sources = self._collector.collect(Market.model_validate(market.model_dump(mode="json")))
        return [str(source.url) for source in sources]

    def fetch_source(self, url: str) -> str:
        return f"Fetched source content from {url}"

    def run(self, run_id: str, market: Market, rules: RuleAnalysis, skeptic: SkepticAssessment) -> ResearchReport:
        canonical_market = self._market_service.get_market_data(market.market_id)
        sources = self._collector.collect(Market.model_validate(canonical_market.model_dump(mode="json")))
        packet = self._synthesizer.build_packet(
            market=Market.model_validate(canonical_market.model_dump(mode="json")),
            sources=sources,
        )
        report = ResearchReport(
            run_id=run_id,
            market_id=market.market_id,
            summary="; ".join(packet.crowd_might_be_wrong[:1] + packet.we_might_be_wrong[:1]),
            source_summary=sources,
            supporting_claims=[claim.claim for claim in packet.supporting_claims],
            opposing_claims=[claim.claim for claim in packet.opposing_claims],
            why_crowd_might_be_wrong=packet.crowd_might_be_wrong,
            why_we_might_be_wrong=packet.we_might_be_wrong,
            risks=rules.risks + skeptic.failure_modes + packet.rule_risk_notes,
            confidence=max(0.0, min(1.0, packet.source_quality_score - skeptic.confidence_penalty / 2)),
        )
        self._research_repo.save(report)
        return report
