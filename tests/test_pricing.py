from polymarket_ai.infra.config import PricingConfig, Settings
from polymarket_ai.infra.providers import HeuristicModelProvider
from polymarket_ai.pricing.service import PricingService
from polymarket_ai.research.collectors import ResearchSynthesizer, StaticResearchCollector
from polymarket_ai.example_data import build_example_market


def test_pricing_blocks_when_edge_is_small() -> None:
    market = build_example_market()
    market.outcomes[0].price = 0.60
    packet = ResearchSynthesizer().build_packet(market, StaticResearchCollector().collect(market))
    service = PricingService(
        provider=HeuristicModelProvider(),
        settings=Settings(),
        pricing_config=PricingConfig(min_edge=0.10, max_uncertainty_width=0.30),
    )

    estimate = service.estimate(market, packet, outcome_id="yes")
    assert estimate.outcome_id == "yes"
    assert estimate.tradeable is False
    assert estimate.no_trade_reason == "edge_too_small"
