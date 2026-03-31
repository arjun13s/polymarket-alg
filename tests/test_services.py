from __future__ import annotations

from polymarket_ai.example_data import build_example_market
from polymarket_ai.hud.models import DecisionKind
from polymarket_ai.models import Market, ResearchReport
from polymarket_ai.services.pricing_service import PricingService


def test_compute_ev_math() -> None:
    market = Market.model_validate(build_example_market().model_dump(mode="json"))
    service = PricingService()
    market_prob, edge, ev = service.compute_ev(market, fair_prob=0.65, fee_bps=100, slippage_bps=50)
    assert market_prob == market.last_price
    assert edge == 0.65 - market_prob
    assert ev == edge - 0.015


def test_estimate_decision_structure() -> None:
    market = Market.model_validate(build_example_market().model_dump(mode="json"))
    report = ResearchReport(
        run_id="run",
        market_id=market.market_id,
        summary="summary",
        source_summary=[],
        supporting_claims=[],
        opposing_claims=[],
        why_crowd_might_be_wrong=[],
        why_we_might_be_wrong=[],
        risks=[],
        confidence=0.8,
    )
    estimate = PricingService().estimate(market, report, fair_prob=0.7, confidence=0.8)
    assert estimate.decision in (DecisionKind.NO_TRADE, DecisionKind.PAPER_TRADE)
    assert estimate.market_id == market.market_id
