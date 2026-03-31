from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from polymarket_ai.market_data.schemas import MarketSnapshot, NormalizedMarket


class MarketAdapter(Protocol):
    source_name: str

    def fetch_markets(self) -> MarketSnapshot:
        ...


@dataclass(slots=True)
class StaticMarketAdapter:
    source_name: str
    markets: list[NormalizedMarket]

    def fetch_markets(self) -> MarketSnapshot:
        return MarketSnapshot(
            as_of=datetime.now(tz=timezone.utc),
            source=self.source_name,
            markets=self.markets,
        )


class GammaApiAdapter:
    source_name = "gamma_api"

    def fetch_markets(self) -> MarketSnapshot:
        raise NotImplementedError("Wire official Gamma API fetch here.")


class DataApiAdapter:
    source_name = "data_api"

    def fetch_markets(self) -> MarketSnapshot:
        raise NotImplementedError("Wire official data API fetch here.")


class ClobOrderbookAdapter:
    source_name = "clob"

    def fetch_markets(self) -> MarketSnapshot:
        raise NotImplementedError("Wire official CLOB fetch here.")
