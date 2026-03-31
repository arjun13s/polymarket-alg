from __future__ import annotations

from polymarket_ai.models import ProbabilityEstimateView, TradeDecision


class RankingService:
    def rank(self, decisions: list[TradeDecision]) -> list[TradeDecision]:
        return sorted(decisions, key=lambda item: (item.expected_value, item.confidence), reverse=True)

    def rank_estimates(self, estimates: list[ProbabilityEstimateView]) -> list[ProbabilityEstimateView]:
        return sorted(estimates, key=lambda item: (item.expected_value, item.confidence), reverse=True)
