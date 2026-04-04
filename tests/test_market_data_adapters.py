from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from polymarket_ai.market_data.adapters import KalshiMarketsAdapter, KalshiTradesAdapter
from polymarket_ai.market_data.schemas import MarketStatus
from polymarket_ai.repositories.market_repo import MarketRepository
from polymarket_ai.services.market_service import MarketService
from polymarket_ai.storage.db import Database


class FakeKalshiMarketsAdapter(KalshiMarketsAdapter):
    def _request_json(self, path: str, params: dict[str, Any] | None) -> Any:
        assert path == "/markets/KXNBAGAME-26APR03MINPHI-MIN"
        assert params is None
        return {
            "market": {
                "ticker": "KXNBAGAME-26APR03MINPHI-MIN",
                "event_ticker": "KXNBAGAME-26APR03MINPHI",
                "series_ticker": "KXNBAGAME",
                "market_type": "binary",
                "title": "Will Minnesota beat Philadelphia?",
                "subtitle": "Minnesota vs Philadelphia",
                "yes_sub_title": "Minnesota",
                "no_sub_title": "Philadelphia",
                "open_time": "2026-04-03T18:00:00Z",
                "close_time": "2026-04-04T02:00:00Z",
                "expiration_time": "2026-04-04T03:00:00Z",
                "status": "active",
                "category": "Sports",
                "rules_primary": "If Minnesota wins, this market resolves to Yes.",
                "rules_secondary": "Determined by the official NBA game result.",
                "settlement_source": "https://www.nba.com/",
                "yes_bid_dollars": "0.5400",
                "yes_ask_dollars": "0.5600",
                "no_bid_dollars": "0.4400",
                "no_ask_dollars": "0.4600",
                "last_price_dollars": "0.5500",
                "volume_fp": "1200.00",
                "volume_24h_fp": "300.00",
                "liquidity_dollars": "5000.00",
                "open_interest_fp": "800.00",
            }
        }


class FakeKalshiTradesAdapter(KalshiTradesAdapter):
    def _fetch_trades(self, ticker: str) -> list[dict[str, Any]]:
        assert ticker == "KXNBAGAME-26APR03MINPHI-MIN"
        return [
            {
                "ticker": ticker,
                "trade_id": "trade-1",
                "count_fp": "20.00",
                "yes_price_dollars": "0.5500",
                "no_price_dollars": "0.4500",
                "taker_side": "yes",
                "created_time": "2026-04-04T01:11:33.387133Z",
            },
            {
                "ticker": ticker,
                "trade_id": "trade-2",
                "count_fp": "10.50",
                "yes_price_dollars": "0.5400",
                "no_price_dollars": "0.4600",
                "taker_side": "no",
                "created_time": "2026-04-04T01:20:33Z",
            },
        ]


def test_kalshi_markets_adapter_normalizes_live_market_payload() -> None:
    market = FakeKalshiMarketsAdapter().fetch_market("KXNBAGAME-26APR03MINPHI-MIN")

    assert market.market_id == "KXNBAGAME-26APR03MINPHI-MIN"
    assert market.event_id == "KXNBAGAME-26APR03MINPHI"
    assert market.slug == "kxnbagame_26apr03minphi_min"
    assert market.event_slug == "kxnbagame_26apr03minphi"
    assert market.status == MarketStatus.OPEN
    assert market.category == "Sports"
    assert market.outcomes[0].outcome_id == "yes"
    assert market.outcomes[0].price == 0.55
    assert market.outcomes[1].outcome_id == "no"
    assert market.outcomes[1].price == 0.45
    assert market.rules.source_url is not None
    assert market.rules.parsed_resolution_criteria
    assert market.best_bid == 0.54
    assert market.best_ask == 0.56
    assert market.spread == 0.02
    assert market.attention_score > 0


def test_kalshi_trades_adapter_enriches_market_trade_activity() -> None:
    market = FakeKalshiMarketsAdapter().fetch_market("KXNBAGAME-26APR03MINPHI-MIN")
    enriched = FakeKalshiTradesAdapter().enrich_market(market)

    assert enriched.recent_trade_count == 2
    assert enriched.recent_buy_volume == 20
    assert enriched.recent_sell_volume == 10.5
    assert enriched.recent_trade_volume == 30.5
    assert enriched.last_activity_at == datetime(2026, 4, 4, 1, 20, 33, tzinfo=timezone.utc)
    assert enriched.attention_score >= market.attention_score


def test_market_service_prefers_live_kalshi_then_trade_enrichment(tmp_path) -> None:
    db = Database(f"sqlite:///{tmp_path / 'market.db'}")
    db.create_all()
    service = MarketService(
        market_repo=MarketRepository(db),
        lookup_adapter=FakeKalshiMarketsAdapter(),
        enrichment_adapters=[FakeKalshiTradesAdapter()],
    )

    market = service.get_market_data("KXNBAGAME-26APR03MINPHI-MIN")

    assert market.market_id == "KXNBAGAME-26APR03MINPHI-MIN"
    assert market.recent_trade_count == 2
    assert market.rules.parsed_resolution_criteria


def test_market_repository_save_is_idempotent_for_same_market_id(tmp_path) -> None:
    db = Database(f"sqlite:///{tmp_path / 'market_repo.db'}")
    db.create_all()
    repo = MarketRepository(db)
    market = FakeKalshiMarketsAdapter().fetch_market("KXNBAGAME-26APR03MINPHI-MIN")

    repo.save(market)
    repo.save(market)

    loaded = repo.get(market.market_id)
    assert loaded is not None
    assert loaded.market_id == market.market_id
