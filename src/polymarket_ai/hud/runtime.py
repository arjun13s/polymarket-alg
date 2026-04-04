from __future__ import annotations

from dataclasses import dataclass

from polymarket_ai.example_data import build_example_market
from polymarket_ai.infra.config import Settings
from polymarket_ai.infra.logging import configure_logging
from polymarket_ai.market_data.adapters import KalshiMarketsAdapter, KalshiTradesAdapter
from polymarket_ai.models import Market
from polymarket_ai.repositories import models as _repository_models  # noqa: F401
from polymarket_ai.repositories.market_repo import MarketRepository
from polymarket_ai.repositories.research_repo import ResearchRepository
from polymarket_ai.repositories.trade_repo import RunRepository, TradeRepository
from polymarket_ai.reliability.cache import TimedCache
from polymarket_ai.services.market_service import MarketService
from polymarket_ai.services.pricing_service import PricingService
from polymarket_ai.services.ranking_service import RankingService
from polymarket_ai.services.research_service import ResearchService
from polymarket_ai.storage.db import Database


@dataclass(slots=True)
class HUDRuntime:
    settings: Settings
    db: Database
    market_repo: MarketRepository
    research_repo: ResearchRepository
    run_repo: RunRepository
    trade_repo: TradeRepository
    market_service: MarketService
    research_service: ResearchService
    pricing_service: PricingService
    ranking_service: RankingService


def build_hud_runtime(settings: Settings | None = None) -> HUDRuntime:
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.log_level)
    db = Database(resolved_settings.resolved_db_url())
    db.create_all()
    market_repo = MarketRepository(db)
    research_repo = ResearchRepository(db)
    run_repo = RunRepository(db)
    trade_repo = TradeRepository(db)
    market_service = MarketService(
        market_repo=market_repo,
        cache=TimedCache[Market](ttl_seconds=resolved_settings.cache_ttl_seconds),
        lookup_adapter=KalshiMarketsAdapter(
            base_url=resolved_settings.kalshi_api_base_url,
            timeout_seconds=resolved_settings.market_api_timeout_seconds,
        ),
        enrichment_adapters=[
            KalshiTradesAdapter(
                base_url=resolved_settings.kalshi_trades_api_base_url,
                timeout_seconds=resolved_settings.market_api_timeout_seconds,
                default_limit=resolved_settings.market_data_trade_limit,
            )
        ],
    )
    research_service = ResearchService(
        market_service=market_service,
        research_repo=research_repo,
    )
    pricing_service = PricingService()
    ranking_service = RankingService()

    example_market = Market.model_validate(build_example_market().model_dump(mode="json"))
    if market_repo.get(example_market.market_id) is None:
        market_service.save_market(example_market)

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
