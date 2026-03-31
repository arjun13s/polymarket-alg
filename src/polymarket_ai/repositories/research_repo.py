from __future__ import annotations

from polymarket_ai.models import ResearchReport
from polymarket_ai.repositories.models import ResearchRecord
from polymarket_ai.storage.db import Database


class ResearchRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, report: ResearchReport) -> None:
        with self._db.session() as session:
            session.add(
                ResearchRecord(
                    run_id=report.run_id or report.market_id,
                    market_id=report.market_id,
                    payload_json=report.model_dump_json(),
                )
            )
