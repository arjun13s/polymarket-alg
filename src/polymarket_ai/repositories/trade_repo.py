from __future__ import annotations

from polymarket_ai.models import RunRecord, TradeDecision
from polymarket_ai.repositories.models import RunRecord as RunTable
from polymarket_ai.repositories.models import TradeRecord
from polymarket_ai.storage.db import Database


class RunRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, run: RunRecord) -> None:
        with self._db.session() as session:
            session.merge(
                RunTable(
                    run_id=run.run_id,
                    market_id=run.market_id,
                    payload_json=run.model_dump_json(),
                    started_at=run.started_at.isoformat(),
                    finished_at=run.finished_at.isoformat(),
                )
            )


class TradeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, decision: TradeDecision) -> None:
        with self._db.session() as session:
            session.add(
                TradeRecord(
                    run_id=decision.run_id,
                    market_id=decision.market_id,
                    decision=str(decision.decision),
                    expected_value=decision.expected_value,
                    payload_json=decision.model_dump_json(),
                )
            )
