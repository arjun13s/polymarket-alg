from __future__ import annotations

from polymarket_ai.market_data.adapters import MarketAdapter
from polymarket_ai.market_data.schemas import MarketSnapshot
from polymarket_ai.storage.repositories import SnapshotRepository


class MarketDataService:
    def __init__(self, adapters: list[MarketAdapter], repository: SnapshotRepository) -> None:
        self._adapters = adapters
        self._repository = repository

    def sync_all(self) -> list[MarketSnapshot]:
        snapshots: list[MarketSnapshot] = []
        for adapter in self._adapters:
            snapshot = adapter.fetch_markets()
            self._repository.save_market_snapshot(snapshot)
            snapshots.append(snapshot)
        return snapshots
