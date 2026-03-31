from __future__ import annotations

import json

from polymarket_ai.app import PipelineService, to_jsonable
from polymarket_ai.bootstrap import AppContainer
from polymarket_ai.example_data import build_example_market
from polymarket_ai.infra.config import Settings


def _build_final_decision_payload(market_ctx, memo, ranked, stake, trade):
    decision = "NO_TRADE"
    if not stake.blocked and stake.stake_dollars > 0 and trade is not None:
        decision = "PAPER_TRADE"
    elif not stake.blocked and memo.pricing.tradeable:
        decision = "WATCHLIST"
    return {
        "market_id": memo.market_id,
        "market_prob": memo.pricing.market_probability,
        "fair_prob": memo.pricing.fair_probability,
        "edge": memo.pricing.edge,
        "confidence": memo.confidence,
        "decision": decision,
        "reasoning_summary": memo.step_logs[-1].summary if memo.step_logs else "",
        "risks": memo.why_we_might_be_wrong + memo.research.rule_risk_notes,
        "sources": [source.model_dump(mode="json") for source in memo.research.source_summaries],
        "snapshot": {
            "snapshot_record_id": market_ctx.snapshot_record_id,
            "snapshot_source": market_ctx.snapshot_source,
            "snapshot_as_of": market_ctx.snapshot_as_of.isoformat(),
        },
        "ranked_score": ranked.score,
        "stake": stake.stake_dollars,
        "paper_trade": trade,
    }


def test_pipeline_emits_structured_decision_payload(tmp_path) -> None:
    settings = Settings(db_url=f"sqlite:///{tmp_path / 'pipeline.db'}", config_path="configs/base.yaml")
    container = AppContainer(settings=settings, example_markets=[build_example_market()])
    container.market_data_service.sync_all()
    pipeline = PipelineService(container)

    market_ctx = pipeline.load_market("atlantic_hurricanes_over_15_2026")
    assert market_ctx is not None

    run_id, memo = pipeline.analyze_market(market_ctx, outcome_id="yes")
    ranked = pipeline.rank_market(market_ctx.market, memo)
    stake, trade = pipeline.paper_trade(run_id, market_ctx.market, memo)

    payload = _build_final_decision_payload(market_ctx, memo, ranked, stake, trade)
    json_payload = to_jsonable(payload)

    assert json_payload["market_id"] == "atlantic_hurricanes_over_15_2026"
    assert json_payload["decision"] in {"NO_TRADE", "WATCHLIST", "PAPER_TRADE"}
    assert isinstance(json_payload["risks"], list)
    assert isinstance(json_payload["sources"], list)
    assert json_payload["sources"]
    assert json_payload["reasoning_summary"]
    assert json.dumps(json_payload)


def test_agentic_step_order_and_reasoning_are_present(tmp_path) -> None:
    settings = Settings(db_url=f"sqlite:///{tmp_path / 'pipeline.db'}", config_path="configs/base.yaml")
    container = AppContainer(settings=settings, example_markets=[build_example_market()])
    container.market_data_service.sync_all()
    pipeline = PipelineService(container)

    market_ctx = pipeline.load_market("atlantic_hurricanes_over_15_2026")
    assert market_ctx is not None

    _, memo = pipeline.analyze_market(market_ctx, outcome_id="yes")

    step_names = [step.step_name for step in memo.step_logs]
    assert step_names == [
        "planner",
        "researcher",
        "skeptic",
        "resolution_rule_check",
        "probability_estimator",
    ]
    assert all(step.summary for step in memo.step_logs)
