from __future__ import annotations

from polymarket_ai.market_data.schemas import NormalizedMarket
from polymarket_ai.research.collectors import ResearchCollector, ResearchSynthesizerProtocol
from polymarket_ai.research.schemas import ResearchPacket
from polymarket_ai.storage.repositories import ResearchRepository


class ResearchService:
    def __init__(
        self,
        collector: ResearchCollector,
        synthesizer: ResearchSynthesizerProtocol,
        repository: ResearchRepository,
    ) -> None:
        self._collector = collector
        self._synthesizer = synthesizer
        self._repository = repository

    def research_market(self, market: NormalizedMarket) -> ResearchPacket:
        sources = self._collector.collect(market)
        packet = self._synthesizer.build_packet(market, sources)
        self._repository.save_research_packet(packet)
        return packet
