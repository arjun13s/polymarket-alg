from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from polymarket_ai.agent.schemas import FinalMemo
from polymarket_ai.infra.config import PortfolioConfig
from polymarket_ai.market_data.schemas import NormalizedMarket


@dataclass(slots=True)
class StakeRecommendation:
    stake_dollars: float
    blocked: bool
    reasons: list[str]


class PortfolioService:
    def __init__(self, config: PortfolioConfig) -> None:
        self._config = config

    def recommend_stake(
        self,
        market: NormalizedMarket,
        memo: FinalMemo,
        current_market_exposure: float = 0.0,
        current_theme_exposure: float = 0.0,
    ) -> StakeRecommendation:
        reasons: list[str] = []
        if not memo.pricing.tradeable:
            reasons.append(memo.pricing.no_trade_reason or "trade_not_allowed")
        if market.liquidity < 1000:
            reasons.append("insufficient_liquidity")
        blocked = len(reasons) > 0
        edge_multiplier = max(memo.pricing.edge, 0.0)
        confidence_multiplier = memo.confidence
        market_cap_remaining = max(
            self._config.bankroll * self._config.max_exposure_per_market - current_market_exposure,
            0.0,
        )
        theme_cap_remaining = max(
            self._config.bankroll * self._config.max_exposure_per_theme - current_theme_exposure,
            0.0,
        )
        cap = min(market_cap_remaining, theme_cap_remaining, market.liquidity * 0.05)
        uncertainty_discount = max(0.1, 1.0 - memo.pricing.uncertainty_width)
        rule_discount = 0.85 if memo.research.rule_risk_notes else 1.0
        time_discount = 1.0
        if market.end_date is not None:
            days_to_resolution = max(
                (market.end_date - datetime.now(tz=timezone.utc)).days,
                1,
            )
            time_discount = max(0.4, min(1.0, 365 / days_to_resolution))
        risk_discount = uncertainty_discount * rule_discount * time_discount
        stake = (
            0.0
            if blocked
            else round(cap * edge_multiplier * confidence_multiplier * risk_discount, 2)
        )
        return StakeRecommendation(stake_dollars=stake, blocked=blocked, reasons=reasons)
