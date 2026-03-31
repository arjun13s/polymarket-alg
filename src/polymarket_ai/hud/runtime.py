from __future__ import annotations

from dataclasses import dataclass, field

from polymarket_ai.hud.config import HUDSettings
from polymarket_ai.infra.paths import resolve_project_path
from polymarket_ai.models import Market
from polymarket_ai.repositories.market_repo import MarketRepository
from polymarket_ai.repositories.research_repo import ResearchRepository
from polymarket_ai.repositories.trade_repo import RunRepository, TradeRepository
from polymarket_ai.reliability.cache import TimedCache
from polymarket_ai.services.market_service import MarketService
from polymarket_ai.services.pricing_service import PricingService
from polymarket_ai.services.ranking_service import RankingService
from polymarket_ai.services.research_service import ResearchService
from polymarket_ai.storage.db import Database
from polymarket_ai.repositories import models as _repository_models  # noqa: F401


@dataclass(slots=True)
class HUDRuntime:
    settings: HUDSettings = field(default_factory=HUDSettings)
    db: Database | None = None
    market_repo: MarketRepository | None = None
    research_repo: ResearchRepository | None = None
    run_repo: RunRepository | None = None
    trade_repo: TradeRepository | None = None
    market_service: MarketService | None = None
    research_service: ResearchService | None = None
    pricing_service: PricingService | None = None
    ranking_service: RankingService | None = None


def build_hud_runtime(settings: HUDSettings | None = None) -> HUDRuntime:
    resolved_settings = settings or HUDSettings()
    db_path = resolve_project_path("data/hud_runtime.db")
    db = Database(f"sqlite:///{db_path}")
    db.create_all()
    market_repo = MarketRepository(db)
    research_repo = ResearchRepository(db)
    run_repo = RunRepository(db)
    trade_repo = TradeRepository(db)
    market_service = MarketService(market_repo=market_repo, cache=TimedCache[Market](ttl_seconds=resolved_settings.market_cache_ttl_seconds))
    research_service = ResearchService(market_service=market_service, research_repo=research_repo)
    pricing_service = PricingService()
    ranking_service = RankingService()
    return HUDRuntime(
        settings=resolved_settings,
        db=db,
        market_repo=market_repo,
        research_repo=research_repo,
        run_repo=run_repo,
        trade_repo=trade_repo,
        market_service=market_service,
        research_service=research_service,
        pricing_service=pricing_service,
        ranking_service=ranking_service,
    )


RUNTIME = build_hud_runtime()
