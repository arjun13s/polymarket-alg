from __future__ import annotations

from dataclasses import dataclass

from polymarket_ai.agent.schemas import FinalMemo
from polymarket_ai.market_data.schemas import NormalizedMarket


@dataclass(slots=True)
class RankedOpportunity:
    market_id: str
    question: str
    score: float
    recommendation: str
    expected_value: float
    confidence: float
    liquidity: float
    risk_notes: list[str]


class RankingService:
    def rank(self, candidates: list[tuple[NormalizedMarket, FinalMemo]]) -> list[RankedOpportunity]:
        ranked: list[RankedOpportunity] = []
        for market, memo in candidates:
            clarity = 1.0 if market.rules.parsed_resolution_criteria else 0.0
            liquidity_score = min(market.liquidity / 50000, 1.0)
            time_score = 0.5 if market.end_date is None else 1.0
            freshness_score = memo.research.evidence_freshness_score
            disagreement_penalty = memo.pricing.uncertainty_width
            attention_penalty = market.attention_score * 0.2
            ev_score = max(min(memo.pricing.expected_value / 0.20, 1.0), -1.0)
            downside_score = max(min(memo.pricing.downside_expected_value / 0.10, 1.0), -1.0)
            score = (
                ev_score * 1.2
                + downside_score * 0.8
                + memo.confidence * 0.9
                + liquidity_score * 0.5
                + clarity * 0.4
                + time_score * 0.1
                + freshness_score * 0.3
                - disagreement_penalty * 0.8
                - attention_penalty
            )
            if not memo.pricing.tradeable:
                score -= 5.0
            ranked.append(
                RankedOpportunity(
                    market_id=market.market_id,
                    question=market.question,
                    score=score,
                    recommendation=memo.recommendation,
                    expected_value=memo.pricing.expected_value,
                    confidence=memo.confidence,
                    liquidity=market.liquidity,
                    risk_notes=memo.why_we_might_be_wrong + memo.research.rule_risk_notes,
                )
            )
        return sorted(ranked, key=lambda item: item.score, reverse=True)
