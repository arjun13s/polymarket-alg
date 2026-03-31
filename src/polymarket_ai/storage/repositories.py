from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from polymarket_ai.agent.schemas import FinalMemo
from polymarket_ai.market_data.schemas import MarketSnapshot, NormalizedMarket
from polymarket_ai.research.schemas import ResearchPacket
from polymarket_ai.storage.db import Database
from polymarket_ai.storage.models import (
    ExecutionDecisionRecord,
    MarketSnapshotRecord,
    PaperTradeRecord,
    RecommendationRecord,
    ResearchRunRecord,
    WorkflowRunRecord,
)


@dataclass(slots=True)
class LoadedMarketContext:
    snapshot_record_id: int
    snapshot_source: str
    snapshot_as_of: datetime
    market: NormalizedMarket


class SnapshotRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save_market_snapshot(self, snapshot: MarketSnapshot) -> None:
        with self._db.session() as session:
            session.add(
                MarketSnapshotRecord(
                    source=snapshot.source,
                    as_of=snapshot.as_of,
                    payload_json=snapshot.model_dump_json(),
                )
            )

    def get_latest_market(self, market_id: str) -> LoadedMarketContext | None:
        with self._db.session() as session:
            records = (
                session.query(MarketSnapshotRecord)
                .order_by(MarketSnapshotRecord.as_of.desc())
                .all()
            )
            for record in records:
                snapshot = MarketSnapshot.model_validate_json(record.payload_json)
                for market in snapshot.markets:
                    if market.market_id == market_id:
                        return LoadedMarketContext(
                            snapshot_record_id=record.id,
                            snapshot_source=record.source,
                            snapshot_as_of=record.as_of,
                            market=market,
                        )
        return None


class ResearchRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save_research_packet(self, packet: ResearchPacket) -> None:
        with self._db.session() as session:
            session.add(
                ResearchRunRecord(
                    market_id=packet.market_id,
                    payload_json=packet.model_dump_json(),
                )
            )


class RecommendationRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save_final_memo(self, memo: FinalMemo) -> None:
        with self._db.session() as session:
            session.add(
                RecommendationRecord(
                    market_id=memo.market_id,
                    outcome_id=memo.outcome_id,
                    recommendation=memo.recommendation,
                    fair_probability=memo.pricing.fair_probability,
                    edge=memo.pricing.edge,
                    confidence=memo.confidence,
                    payload_json=memo.model_dump_json(),
                )
            )

    def list_recommendations(self) -> list[dict[str, object]]:
        with self._db.session() as session:
            records = session.query(RecommendationRecord).all()
            return [json.loads(record.payload_json) for record in records]


class PaperTradeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save_trade(self, run_id: str, trade: dict[str, object]) -> None:
        with self._db.session() as session:
            session.add(
                PaperTradeRecord(
                    run_id=run_id,
                    market_id=str(trade["market_id"]),
                    outcome_id=str(trade["outcome_id"]),
                    side=str(trade["side"]),
                    stake=float(trade["stake"]),
                    payload_json=json.dumps(trade, default=str),
                )
            )


class WorkflowRunRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create_run(self, payload: dict[str, object]) -> None:
        with self._db.session() as session:
            session.add(
                WorkflowRunRecord(
                    run_id=str(payload["run_id"]),
                    market_id=str(payload["market_id"]),
                    outcome_id=str(payload["outcome_id"]),
                    snapshot_record_id=int(payload["snapshot_record_id"]),
                    snapshot_as_of=str(payload["snapshot_as_of"]),
                    status=str(payload["status"]),
                    started_at=str(payload["started_at"]),
                    finished_at=str(payload["finished_at"]),
                    payload_json=json.dumps(payload, default=str),
                )
            )

    def update_run(self, run_id: str, payload: dict[str, object]) -> None:
        with self._db.session() as session:
            record = session.query(WorkflowRunRecord).filter_by(run_id=run_id).one()
            record.status = str(payload["status"])
            record.finished_at = str(payload["finished_at"])
            record.payload_json = json.dumps(payload, default=str)


class ExecutionDecisionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save_decision(self, payload: dict[str, object]) -> None:
        with self._db.session() as session:
            session.add(
                ExecutionDecisionRecord(
                    run_id=str(payload["run_id"]),
                    market_id=str(payload["market_id"]),
                    outcome_id=str(payload["outcome_id"]),
                    blocked=str(payload["blocked"]),
                    recommended_stake=float(payload["recommended_stake"]),
                    execution_status=str(payload["execution_status"]),
                    payload_json=json.dumps(payload, default=str),
                )
            )
