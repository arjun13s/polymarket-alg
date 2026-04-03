from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from polymarket_ai.market_data.adapters import DataApiAdapter, GammaApiAdapter
from polymarket_ai.market_data.schemas import MarketStatus
from polymarket_ai.repositories.market_repo import MarketRepository
from polymarket_ai.services.market_service import MarketService
from polymarket_ai.storage.db import Database


class FakeGammaAdapter(GammaApiAdapter):
    def _request_json(self, path: str, params: dict[str, Any] | None) -> Any:
        assert path == "/markets"
        assert params in (
            {"id": "540816"},
            {"slug": "russia-ukraine-ceasefire-before-gta-vi-554"},
        )
        return {
            "id": "540816",
            "slug": "russia-ukraine-ceasefire-before-gta-vi-554",
            "question": "Russia-Ukraine Ceasefire before GTA VI?",
            "conditionId": "0x9c1a953fe92c8357f1b646ba25d983aa83e90c525992db14fb726fa895cb5763",
            "description": "This market resolves to Yes if an official ceasefire is announced.\n\nSource: official statements.",
            "resolutionSource": "https://www.un.org/",
            "endDate": "2026-07-31T12:00:00Z",
            "category": "Politics",
            "active": True,
            "closed": False,
            "liquidityNum": 53063.28,
            "volume24hr": 1782.84,
            "volumeNum": 1412094.92,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.545", "0.455"]',
            "clobTokenIds": '["8501497159083948713316135768103773293754490207922884688769443031624417212426", "2527312495175492857904889758552137141356236738032676480522356889996545113869"]',
            "bestBid": 0.54,
            "bestAsk": 0.55,
            "lastTradePrice": 0.54,
            "spread": 0.01,
            "competitive": 0.99,
            "events": [
                {
                    "id": "23784",
                    "slug": "what-will-happen-before-gta-vi",
                    "category": "Politics",
                    "commentCount": 795,
                }
            ],
        }


class FakeDataApiAdapter(DataApiAdapter):
    def _fetch_trades(self, condition_id: str) -> list[dict[str, Any]]:
        assert condition_id == "0x9c1a953fe92c8357f1b646ba25d983aa83e90c525992db14fb726fa895cb5763"
        return [
            {
                "conditionId": condition_id,
                "side": "BUY",
                "size": 20,
                "timestamp": 1775171649,
            },
            {
                "conditionId": condition_id,
                "side": "SELL",
                "size": 10.5,
                "timestamp": 1775174097,
            },
        ]


def test_gamma_adapter_normalizes_live_market_payload() -> None:
    market = FakeGammaAdapter().fetch_market("540816")
    assert market.market_id == "russia-ukraine-ceasefire-before-gta-vi-554"
    assert market.condition_id == "0x9c1a953fe92c8357f1b646ba25d983aa83e90c525992db14fb726fa895cb5763"
    assert market.event_id == "23784"
    assert market.event_slug == "what-will-happen-before-gta-vi"
    assert market.status == MarketStatus.OPEN
    assert market.outcomes[0].outcome_id == "yes"
    assert market.outcomes[0].token_id
    assert market.rules.source_url is not None
    assert market.best_bid == 0.54
    assert market.best_ask == 0.55
    assert market.attention_score > 0


def test_data_api_adapter_enriches_market_trade_activity() -> None:
    market = FakeGammaAdapter().fetch_market("540816")
    enriched = FakeDataApiAdapter().enrich_market(market)
    assert enriched.recent_trade_count == 2
    assert enriched.recent_buy_volume == 20
    assert enriched.recent_sell_volume == 10.5
    assert enriched.recent_trade_volume == 30.5
    assert enriched.last_activity_at == datetime.fromtimestamp(1775174097, tz=timezone.utc)
    assert enriched.attention_score >= market.attention_score


def test_market_service_prefers_live_gamma_then_data_enrichment(tmp_path) -> None:
    db = Database(f"sqlite:///{tmp_path / 'market.db'}")
    db.create_all()
    service = MarketService(
        market_repo=MarketRepository(db),
        lookup_adapter=FakeGammaAdapter(),
        enrichment_adapters=[FakeDataApiAdapter()],
    )

    market = service.get_market_data("540816")

    assert market.market_id == "russia-ukraine-ceasefire-before-gta-vi-554"
    assert market.recent_trade_count == 2
    assert market.rules.parsed_resolution_criteria


def test_market_repository_save_is_idempotent_for_same_market_id(tmp_path) -> None:
    db = Database(f"sqlite:///{tmp_path / 'market_repo.db'}")
    db.create_all()
    repo = MarketRepository(db)
    market = FakeGammaAdapter().fetch_market("540816")

    repo.save(market)
    repo.save(market)

    loaded = repo.get(market.market_id)
    assert loaded is not None
    assert loaded.market_id == market.market_id
