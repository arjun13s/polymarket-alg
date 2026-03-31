from polymarket_ai.app import PipelineService, to_jsonable
from polymarket_ai.bootstrap import AppContainer
from polymarket_ai.example_data import build_example_market
from polymarket_ai.infra.config import Settings
from polymarket_ai.storage.models import (
    ExecutionDecisionRecord,
    MarketSnapshotRecord,
    PaperTradeRecord,
    RecommendationRecord,
    ResearchRunRecord,
    WorkflowRunRecord,
)


def test_example_pipeline_persists_and_serializes(tmp_path) -> None:
    settings = Settings(
        db_url=f"sqlite:///{tmp_path / 'test.db'}",
        config_path="configs/base.yaml",
    )
    container = AppContainer(settings=settings, example_markets=[build_example_market()])
    container.market_data_service.sync_all()
    pipeline = PipelineService(container)

    market_ctx = pipeline.load_market("atlantic_hurricanes_over_15_2026")

    assert market_ctx is not None
    run_id, memo = pipeline.analyze_market(market_ctx, outcome_id="yes")
    stake, trade = pipeline.paper_trade(run_id, market_ctx.market, memo)
    ranked = pipeline.rank_market(market_ctx.market, memo)

    assert to_jsonable(memo)["market_id"] == "atlantic_hurricanes_over_15_2026"
    assert stake.stake_dollars >= 0.0
    assert ranked.market_id == market_ctx.market.market_id
    assert trade is None or trade["market_id"] == market_ctx.market.market_id

    with container.db.session() as session:
        assert session.query(MarketSnapshotRecord).count() == 1
        assert session.query(ResearchRunRecord).count() == 1
        assert session.query(RecommendationRecord).count() == 1
        assert session.query(WorkflowRunRecord).count() == 1
        assert session.query(ExecutionDecisionRecord).count() == 1
        if trade is not None:
            assert session.query(PaperTradeRecord).count() == 1
