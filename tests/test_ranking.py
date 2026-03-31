from polymarket_ai.agent.schemas import FinalMemo, WorkflowStepLog
from polymarket_ai.example_data import build_example_market
from polymarket_ai.pricing.schemas import ProbabilityEstimate
from polymarket_ai.ranking.service import RankingService
from polymarket_ai.research.collectors import ResearchSynthesizer, StaticResearchCollector


def test_ranking_prefers_higher_ev() -> None:
    market = build_example_market()
    research = ResearchSynthesizer().build_packet(market, StaticResearchCollector().collect(market))
    high_ev = FinalMemo(
        market_id=market.market_id,
        outcome_id="yes",
        recommendation="buy_yes",
        confidence=0.8,
        why_crowd_might_be_wrong=[],
        why_we_might_be_wrong=[],
        resolution_rule_check=research.rules_summary,
        source_quality_notes=[],
        research=research,
        pricing=ProbabilityEstimate(
            outcome_id="yes",
            executable_price=0.42,
            fee_and_slippage_cost=0.04,
            market_probability=0.4,
            fair_probability=0.6,
            lower_bound=0.52,
            upper_bound=0.68,
            edge=0.2,
            expected_value=0.16,
            downside_expected_value=0.06,
            uncertainty_width=0.16,
            tradeable=True,
            rationale="x",
        ),
        step_logs=[WorkflowStepLog(step_name="x", status="completed", summary="x")],
    )
    low_ev = high_ev.model_copy(deep=True)
    low_ev.pricing.expected_value = 0.03
    low_ev.pricing.edge = 0.04

    ranked = RankingService().rank([(market, low_ev), (market, high_ev)])

    assert ranked[0].expected_value == 0.16
