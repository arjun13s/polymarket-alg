from __future__ import annotations

from fastapi import FastAPI

from polymarket_ai.hud.app import create_hud_app

hud_app = create_hud_app()
app = FastAPI(title="polymarket-ai-system", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/analyze/{market_id}")
def analyze_market(market_id: str, outcome_id: str = "yes") -> dict[str, object]:
    return hud_app.orchestrator.analyze_market(market_id, outcome_id=outcome_id).model_dump(mode="json")
