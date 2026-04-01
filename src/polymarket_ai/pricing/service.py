from __future__ import annotations

from polymarket_ai.infra.config import PricingConfig, Settings
from polymarket_ai.infra.providers import ModelProvider
from polymarket_ai.market_data.schemas import NormalizedMarket
from polymarket_ai.pricing.schemas import ProbabilityEstimate
from polymarket_ai.research.schemas import ResearchPacket


class PricingService:
    def __init__(
        self,
        provider: ModelProvider,
        settings: Settings,
        pricing_config: PricingConfig,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._pricing_config = pricing_config

    @staticmethod
    def implied_probability(price: float) -> float:
        return max(min(price, 1.0), 0.0)

    @staticmethod
    def estimate_execution_slippage(liquidity: float) -> float:
        if liquidity <= 0:
            return 0.05
        return min(0.05, 500 / max(liquidity, 1.0) * 0.01)

    def estimate(
        self,
        market: NormalizedMarket,
        research: ResearchPacket,
        outcome_id: str,
    ) -> ProbabilityEstimate:
        outcome = next((item for item in market.outcomes if item.outcome_id == outcome_id), None)
        if outcome is None:
            raise ValueError(f"Unknown outcome_id {outcome_id!r} for market {market.market_id}")
        market_probability = self.implied_probability(outcome.price)
        executable_price = self.implied_probability(max(market.best_ask or 0.0, outcome.price))
        assessment = self._provider.estimate_probability(research, outcome_id=outcome_id)
        fair_probability, lower, upper, rationale = (
            assessment.fair_probability,
            assessment.lower_bound,
            assessment.upper_bound,
            assessment.rationale,
        )
        edge = fair_probability - executable_price
        fee_cost = self._settings.default_fee_bps / 10000
        configured_slippage = self._settings.default_slippage_bps / 10000
        execution_slippage = max(configured_slippage, self.estimate_execution_slippage(market.liquidity))
        trading_cost = fee_cost + execution_slippage
        expected_value = edge - trading_cost
        downside_expected_value = (lower - executable_price) - trading_cost
        uncertainty_width = upper - lower
        tradeable = True
        no_trade_reason: str | None = None
        if uncertainty_width > self._pricing_config.max_uncertainty_width:
            tradeable = False
            no_trade_reason = "uncertainty_too_high"
        elif edge < self._pricing_config.min_edge:
            tradeable = False
            no_trade_reason = "edge_too_small"
        elif downside_expected_value <= 0:
            tradeable = False
            no_trade_reason = "downside_ev_not_positive"
        return ProbabilityEstimate(
            outcome_id=outcome_id,
            executable_price=executable_price,
            fee_and_slippage_cost=trading_cost,
            market_probability=market_probability,
            fair_probability=fair_probability,
            lower_bound=lower,
            upper_bound=upper,
            edge=edge,
            expected_value=expected_value,
            downside_expected_value=downside_expected_value,
            uncertainty_width=uncertainty_width,
            tradeable=tradeable,
            no_trade_reason=no_trade_reason,
            rationale=rationale,
        )
