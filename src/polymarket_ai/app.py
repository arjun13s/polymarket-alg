from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from polymarket_ai.agent.schemas import FinalMemo
from polymarket_ai.bootstrap import AppContainer
from polymarket_ai.execution.paper import PaperExecutionService
from polymarket_ai.market_data.schemas import NormalizedMarket
from polymarket_ai.portfolio.service import StakeRecommendation
from polymarket_ai.ranking.service import RankedOpportunity
from polymarket_ai.storage.repositories import LoadedMarketContext


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
        for key, item in payload.items():
            if hasattr(item, "isoformat"):
                payload[key] = item.isoformat()
        return payload
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


class PipelineService:
    def __init__(self, container: AppContainer) -> None:
        self._container = container
        self._paper = PaperExecutionService()

    def load_market(self, market_id: str) -> LoadedMarketContext | None:
        return self._container.snapshot_repository.get_latest_market(market_id)

    def _create_run(self, market_ctx: LoadedMarketContext, outcome_id: str) -> str:
        run_id = str(uuid4())
        now = datetime.now(tz=timezone.utc).isoformat()
        self._container.workflow_run_repository.create_run(
            {
                "run_id": run_id,
                "market_id": market_ctx.market.market_id,
                "outcome_id": outcome_id,
                "snapshot_record_id": market_ctx.snapshot_record_id,
                "snapshot_as_of": market_ctx.snapshot_as_of.isoformat(),
                "status": "started",
                "started_at": now,
                "finished_at": now,
            }
        )
        return run_id

    def _finish_run(self, run_id: str, market_ctx: LoadedMarketContext, outcome_id: str, status: str) -> None:
        self._container.workflow_run_repository.update_run(
            run_id,
            {
                "run_id": run_id,
                "market_id": market_ctx.market.market_id,
                "outcome_id": outcome_id,
                "snapshot_record_id": market_ctx.snapshot_record_id,
                "snapshot_as_of": market_ctx.snapshot_as_of.isoformat(),
                "status": status,
                "started_at": "",
                "finished_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )

    def analyze_market(self, market_ctx: LoadedMarketContext, outcome_id: str) -> tuple[str, FinalMemo]:
        run_id = self._create_run(market_ctx, outcome_id=outcome_id)
        try:
            memo = self._container.agent_workflow.run(market_ctx.market, outcome_id=outcome_id)
        except Exception:
            self._finish_run(run_id, market_ctx, outcome_id=outcome_id, status="failed")
            raise
        self._container.recommendation_repository.save_final_memo(memo)
        self._finish_run(run_id, market_ctx, outcome_id=outcome_id, status="analyzed")
        return run_id, memo

    def rank_market(self, market: NormalizedMarket, memo: FinalMemo) -> RankedOpportunity:
        return self._container.ranking_service.rank([(market, memo)])[0]

    def paper_trade(
        self,
        run_id: str,
        market: NormalizedMarket,
        memo: FinalMemo,
    ) -> tuple[StakeRecommendation, dict[str, object] | None]:
        stake = self._container.portfolio_service.recommend_stake(market, memo)
        trade = self._paper.place_paper_trade(
            market_id=market.market_id,
            outcome_id=memo.outcome_id,
            side=memo.recommendation,
            stake=stake,
        )
        trade_payload = None if trade is None else to_jsonable(trade)
        self._container.execution_decision_repository.save_decision(
            {
                "run_id": run_id,
                "market_id": market.market_id,
                "outcome_id": memo.outcome_id,
                "blocked": stake.blocked,
                "recommended_stake": stake.stake_dollars,
                "reasons": stake.reasons,
                "execution_status": "paper_submitted" if trade_payload is not None else "no_trade",
            }
        )
        if trade_payload is not None:
            self._container.paper_trade_repository.save_trade(run_id, trade_payload)
        return stake, trade_payload
