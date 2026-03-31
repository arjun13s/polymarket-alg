from __future__ import annotations

import json
from pathlib import Path

import typer

from polymarket_ai.hud.environment import prediction_market_env
from polymarket_ai.hud.orchestrator import PredictionMarketOrchestrator
from polymarket_ai.hud.scenarios import (
    full_pipeline_scenario,
    probability_scenario,
    research_scenario,
    rules_scenario,
    skeptic_scenario,
)

app = typer.Typer(no_args_is_help=True)
orchestrator = PredictionMarketOrchestrator()


@app.command("analyze-market")
def analyze_market(market_id: str) -> None:
    decision = orchestrator.analyze_market(market_id)
    print(decision.model_dump_json(indent=2))


@app.command("run-daily-batch")
def run_daily_batch(market_id: str = "atlantic_hurricanes_over_15_2026") -> None:
    decision = orchestrator.analyze_market(market_id)
    print(decision.model_dump_json(indent=2))


@app.command("rank-opportunities")
def rank_opportunities(market_id: str = "atlantic_hurricanes_over_15_2026") -> None:
    decision = orchestrator.analyze_market(market_id)
    print(json.dumps({"market_id": market_id, "decision": decision.model_dump(mode="json")}, indent=2))


@app.command("run-evals")
def run_evals(output_file: Path | None = None) -> None:
    result = prediction_market_env.run_scenario("full_pipeline_scenario", market_id="atlantic_hurricanes_over_15_2026")
    payload = result.model_dump(mode="json")
    if output_file is not None:
        output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


@app.command("run_tests")
def run_tests() -> None:
    try:
        import pytest  # type: ignore

        exit_code = pytest.main(["tests"])
        print(json.dumps({"status": "pytest", "exit_code": exit_code}, indent=2))
        return
    except Exception:
        results = {
            "rules": prediction_market_env.run_scenario("rules_scenario", market_id="atlantic_hurricanes_over_15_2026").score,
            "research": prediction_market_env.run_scenario("research_scenario", market_id="atlantic_hurricanes_over_15_2026").score,
            "skeptic": prediction_market_env.run_scenario("skeptic_scenario", market_id="atlantic_hurricanes_over_15_2026").score,
            "probability": prediction_market_env.run_scenario("probability_scenario", market_id="atlantic_hurricanes_over_15_2026").score,
        }
        print(json.dumps({"status": "fallback_scenarios", "results": results}, indent=2))


@app.command("run_eval_suite")
def run_eval_suite(output_file: Path | None = None) -> None:
    outputs = {
        name: prediction_market_env.run_scenario(name, market_id="atlantic_hurricanes_over_15_2026").model_dump(mode="json")
        for name in [
            "rules_scenario",
            "research_scenario",
            "skeptic_scenario",
            "probability_scenario",
            "full_pipeline_scenario",
        ]
    }
    if output_file is not None:
        output_file.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    print(json.dumps(outputs, indent=2))


__all__ = [
    "app",
    "analyze_market",
    "rank_opportunities",
    "run_daily_batch",
    "run_evals",
    "run_tests",
    "run_eval_suite",
]


if __name__ == "__main__":
    app()
