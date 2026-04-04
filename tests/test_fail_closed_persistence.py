from __future__ import annotations

from pathlib import Path

from polymarket_ai.hud.app import create_hud_app
from polymarket_ai.hud.models import DecisionKind
from polymarket_ai.infra.config import Settings
from polymarket_ai.repositories.models import RunRecord as RunTable
from polymarket_ai.repositories.models import TradeRecord


def test_orchestrator_fails_closed_when_run_persistence_breaks(tmp_path: Path) -> None:
    settings = Settings(db_url=f"sqlite:///{tmp_path / 'hud.db'}", config_path="configs/base.yaml")
    hud_app = create_hud_app(settings=settings)

    def broken_save(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("run persistence unavailable")

    hud_app.runtime.run_repo.save = broken_save  # type: ignore[method-assign]

    decision = hud_app.orchestrator.analyze_market("KXATLANTICSTORMS-26-N16")

    assert decision.decision == DecisionKind.NO_TRADE
    assert "fallback" in decision.reasoning_summary.lower()

    with hud_app.runtime.db.session() as session:
        assert session.query(RunTable).count() == 0
        assert session.query(TradeRecord).count() == 0
