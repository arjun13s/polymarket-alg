from __future__ import annotations

import json

from polymarket_ai.models import Market
from polymarket_ai.repositories.models import MarketRecord
from polymarket_ai.storage.db import Database


class MarketRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, market: Market) -> None:
        with self._db.session() as session:
            existing = session.query(MarketRecord).filter_by(market_id=market.market_id).one_or_none()
            if existing is None:
                session.add(
                    MarketRecord(
                        market_id=market.market_id,
                        payload_json=market.model_dump_json(),
                    )
                )
                return
            existing.payload_json = market.model_dump_json()

    def get(self, market_id: str) -> Market | None:
        with self._db.session() as session:
            record = session.query(MarketRecord).filter_by(market_id=market_id).one_or_none()
            if record is None:
                return None
            return Market.model_validate_json(record.payload_json)

    def list_all(self) -> list[Market]:
        with self._db.session() as session:
            return [Market.model_validate_json(record.payload_json) for record in session.query(MarketRecord).all()]
