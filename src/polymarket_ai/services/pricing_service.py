from __future__ import annotations

from polymarket_ai.hud.models import DecisionKind
from polymarket_ai.models import Market, ProbabilityEstimateView, ResearchReport


class PricingService:
    def compute_ev(
        self,
        market: Market,
        fair_prob: float,
        fee_bps: int,
        slippage_bps: int,
    ) -> tuple[float, float, float]:
        market_prob = market.last_price or market.best_ask or 0.5
        cost = (fee_bps + slippage_bps) / 10000
        edge = fair_prob - market_prob
        ev = edge - cost
        return market_prob, edge, ev

    def estimate(
        self,
        market: Market,
        research: ResearchReport,
        fair_prob: float,
        confidence: float,
        fee_bps: int = 150,
        slippage_bps: int = 50,
    ) -> ProbabilityEstimateView:
        market_prob, edge, ev = self.compute_ev(market, fair_prob, fee_bps, slippage_bps)
        decision = DecisionKind.PAPER_TRADE if confidence >= 0.65 and edge >= 0.05 else DecisionKind.NO_TRADE
        return ProbabilityEstimateView(
            market_id=market.market_id,
            fair_prob=fair_prob,
            market_prob=market_prob,
            edge=edge,
            confidence=confidence,
            expected_value=ev,
            decision=decision,
            reasoning_summary=research.summary,
            risks=research.risks,
            sources=[source.url.unicode_string() for source in research.source_summary],
        )
