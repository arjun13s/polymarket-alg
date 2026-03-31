from __future__ import annotations

from polymarket_ai.example_data import build_example_market
from polymarket_ai.models import Market
from polymarket_ai.reliability.cache import TimedCache
from polymarket_ai.repositories.market_repo import MarketRepository


class MarketService:
    def __init__(self, market_repo: MarketRepository, cache: TimedCache[Market] | None = None) -> None:
        self._market_repo = market_repo
        self._cache = cache or TimedCache[Market](ttl_seconds=300)

    def get_market_data(self, market_id: str) -> Market:
        def loader() -> Market:
            stored = self._market_repo.get(market_id)
            if stored is not None:
                return stored
            example = build_example_market()
            if example.market_id != market_id:
                raise KeyError(f"Unknown market_id {market_id}")
            return Market.model_validate(example.model_dump(mode="json"))

        return self._cache.get_or_set(market_id, loader)

    def save_market(self, market: Market) -> None:
        self._market_repo.save(market)
        self._cache.set(market.market_id, market, ttl_seconds=300)
