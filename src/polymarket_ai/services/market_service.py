from __future__ import annotations

from polymarket_ai.example_data import build_example_market
from polymarket_ai.market_data.adapters import MarketEnrichmentAdapter, MarketLookupAdapter
from polymarket_ai.models import Market
from polymarket_ai.reliability.cache import TimedCache
from polymarket_ai.repositories.market_repo import MarketRepository


class MarketService:
    def __init__(
        self,
        market_repo: MarketRepository,
        cache: TimedCache[Market] | None = None,
        lookup_adapter: MarketLookupAdapter | None = None,
        enrichment_adapters: list[MarketEnrichmentAdapter] | None = None,
    ) -> None:
        self._market_repo = market_repo
        self._cache = cache or TimedCache[Market](ttl_seconds=300)
        self._lookup_adapter = lookup_adapter
        self._enrichment_adapters = enrichment_adapters or []

    def get_market_data(self, market_id: str) -> Market:
        def loader() -> Market:
            live_market = self._fetch_live_market(market_id)
            if live_market is not None:
                self.save_market(live_market)
                return live_market

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

    def _fetch_live_market(self, market_id: str) -> Market | None:
        if self._lookup_adapter is None:
            return None
        try:
            market = Market.model_validate(
                self._lookup_adapter.fetch_market(market_id).model_dump(mode="json")
            )
            for adapter in self._enrichment_adapters:
                market = Market.model_validate(adapter.enrich_market(market).model_dump(mode="json"))
            return market
        except Exception:
            return None
