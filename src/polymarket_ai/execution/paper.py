from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from polymarket_ai.portfolio.service import StakeRecommendation


@dataclass(slots=True)
class PaperTrade:
    market_id: str
    outcome_id: str
    side: str
    stake: float
    created_at: datetime
    notes: str


class PaperExecutionService:
    def place_paper_trade(
        self,
        market_id: str,
        outcome_id: str,
        side: str,
        stake: StakeRecommendation,
    ) -> PaperTrade | None:
        if stake.blocked or stake.stake_dollars <= 0:
            return None
        return PaperTrade(
            market_id=market_id,
            outcome_id=outcome_id,
            side=side,
            stake=stake.stake_dollars,
            created_at=datetime.now(tz=timezone.utc),
            notes="Paper trade only. No live order submitted.",
        )
