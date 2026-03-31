from __future__ import annotations

from dataclasses import dataclass, field

from polymarket_ai.agent.workflow import AgentWorkflow
from polymarket_ai.infra.config import Settings
from polymarket_ai.infra.logging import configure_logging
from polymarket_ai.infra.providers import HeuristicModelProvider, ModelProvider, create_default_provider
from polymarket_ai.market_data.adapters import MarketAdapter, StaticMarketAdapter
from polymarket_ai.market_data.schemas import MarketSnapshot, NormalizedMarket
from polymarket_ai.market_data.service import MarketDataService
from polymarket_ai.portfolio.service import PortfolioService
from polymarket_ai.pricing.service import PricingService
from polymarket_ai.ranking.service import RankingService
from polymarket_ai.research.collectors import (
    ResearchCollector,
    ResearchSynthesizer,
    ResearchSynthesizerProtocol,
    StaticResearchCollector,
)
from polymarket_ai.research.service import ResearchService
from polymarket_ai.storage.db import Database
from polymarket_ai.storage.repositories import (
    ExecutionDecisionRepository,
    PaperTradeRepository,
    RecommendationRepository,
    ResearchRepository,
    SnapshotRepository,
    WorkflowRunRepository,
)


@dataclass(slots=True)
class RuntimeComponents:
    market_adapters: list[MarketAdapter] = field(default_factory=list)
    research_collector: ResearchCollector = field(default_factory=StaticResearchCollector)
    research_synthesizer: ResearchSynthesizerProtocol = field(default_factory=ResearchSynthesizer)
    model_provider: ModelProvider = field(default_factory=HeuristicModelProvider)


class AppContainer:
    def __init__(
        self,
        settings: Settings,
        runtime: RuntimeComponents | None = None,
        example_markets: list[NormalizedMarket] | None = None,
    ) -> None:
        file_config = settings.load_file_config()
        configure_logging(settings.log_level)
        runtime = runtime or RuntimeComponents()
        if isinstance(runtime.model_provider, HeuristicModelProvider):
            runtime.model_provider = create_default_provider(settings, file_config.system.provider)
        if not runtime.market_adapters and example_markets is not None:
            runtime.market_adapters = [
                StaticMarketAdapter(
                    source_name="static_example",
                    markets=example_markets,
                )
            ]
        self.settings = settings
        self.db = Database(settings.resolved_db_url())
        self.db.create_all()
        self.snapshot_repository = SnapshotRepository(self.db)
        self.research_repository = ResearchRepository(self.db)
        self.recommendation_repository = RecommendationRepository(self.db)
        self.paper_trade_repository = PaperTradeRepository(self.db)
        self.workflow_run_repository = WorkflowRunRepository(self.db)
        self.execution_decision_repository = ExecutionDecisionRepository(self.db)
        self.market_data_service = MarketDataService(
            adapters=runtime.market_adapters,
            repository=self.snapshot_repository,
        )
        self.research_service = ResearchService(
            collector=runtime.research_collector,
            synthesizer=runtime.research_synthesizer,
            repository=self.research_repository,
        )
        self.pricing_service = PricingService(
            provider=runtime.model_provider,
            settings=settings,
            pricing_config=file_config.pricing,
        )
        self.agent_workflow = AgentWorkflow(
            research_service=self.research_service,
            pricing_service=self.pricing_service,
        )
        self.ranking_service = RankingService()
        self.portfolio_service = PortfolioService(file_config.portfolio)
