from __future__ import annotations

from polymarket_ai.app import to_jsonable
from polymarket_ai.example_data import build_example_market
from polymarket_ai.pricing.service import PricingService
from polymarket_ai.infra.config import PricingConfig, Settings
from polymarket_ai.infra.providers import HeuristicModelProvider
from polymarket_ai.research.collectors import ResearchSynthesizer, StaticResearchCollector


def test_output_contract_contains_expected_fields() -> None:
    market = build_example_market()
    research = ResearchSynthesizer().build_packet(market, StaticResearchCollector().collect(market))
    estimate = PricingService(
        provider=HeuristicModelProvider(),
        settings=Settings(),
        pricing_config=PricingConfig(),
    ).estimate(market, research, outcome_id="yes")

    payload = to_jsonable(
        {
            "market_id": market.market_id,
            "market_prob": estimate.market_probability,
            "fair_prob": estimate.fair_probability,
            "edge": estimate.edge,
            "confidence": 0.75,
            "decision": "WATCHLIST",
            "reasoning_summary": "Structured research and pricing output.",
            "risks": ["resolution ambiguity"],
            "sources": [source.model_dump(mode="json") for source in research.source_summaries],
        }
    )

    assert set(payload) >= {
        "market_id",
        "market_prob",
        "fair_prob",
        "edge",
        "confidence",
        "decision",
        "reasoning_summary",
        "risks",
        "sources",
    }
    assert payload["decision"] in {"NO_TRADE", "WATCHLIST", "PAPER_TRADE"}
    assert payload["sources"]
