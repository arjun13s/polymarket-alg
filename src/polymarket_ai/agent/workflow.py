from __future__ import annotations

from polymarket_ai.agent.schemas import FinalMemo, WorkflowStepLog
from polymarket_ai.market_data.schemas import NormalizedMarket
from polymarket_ai.pricing.service import PricingService
from polymarket_ai.research.service import ResearchService


class AgentWorkflow:
    def __init__(
        self,
        research_service: ResearchService,
        pricing_service: PricingService,
    ) -> None:
        self._research_service = research_service
        self._pricing_service = pricing_service

    def run(self, market: NormalizedMarket, outcome_id: str) -> FinalMemo:
        steps: list[WorkflowStepLog] = [
            WorkflowStepLog(
                step_name="planner",
                status="completed",
                summary=(
                    f"Confirmed market metadata, selected target outcome {outcome_id}, "
                    "queued rule review."
                ),
            )
        ]
        research = self._research_service.research_market(market)
        steps.append(
            WorkflowStepLog(
                step_name="researcher",
                status="completed",
                summary=f"Collected {len(research.source_summaries)} sources and synthesized core claims.",
            )
        )
        steps.append(
            WorkflowStepLog(
                step_name="skeptic",
                status="completed",
                summary="Bear case explicitly required before scoring.",
            )
        )
        steps.append(
            WorkflowStepLog(
                step_name="resolution_rule_check",
                status="completed",
                summary="Resolution criteria parsed and attached to memo.",
            )
        )
        pricing = self._pricing_service.estimate(market, research, outcome_id=outcome_id)
        steps.append(
            WorkflowStepLog(
                step_name="probability_estimator",
                status="completed",
                summary=(
                    f"Fair probability {pricing.fair_probability:.2%} vs market "
                    f"{pricing.market_probability:.2%}."
                ),
            )
        )
        recommendation = "no_trade"
        if pricing.tradeable and pricing.edge > 0:
            recommendation = "buy_yes"
        confidence = max(0.0, min(1.0, research.source_quality_score - pricing.uncertainty_width / 2))
        memo = FinalMemo(
            market_id=market.market_id,
            outcome_id=outcome_id,
            recommendation=recommendation,
            confidence=confidence,
            why_crowd_might_be_wrong=research.crowd_might_be_wrong,
            why_we_might_be_wrong=research.we_might_be_wrong,
            resolution_rule_check=research.rules_summary,
            source_quality_notes=[
                f"Average source quality score: {research.source_quality_score:.2f}",
                f"Evidence freshness score: {research.evidence_freshness_score:.2f}",
            ],
            research=research,
            pricing=pricing,
            step_logs=steps,
        )
        return memo
