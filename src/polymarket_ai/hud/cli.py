from __future__ import annotations

import json
from pathlib import Path

import typer

from polymarket_ai.hud.app import create_hud_app

app = typer.Typer(no_args_is_help=True)


def _build_app():
    return create_hud_app()


@app.command("analyze-market")
def analyze_market(market_id: str, outcome_id: str = "yes") -> None:
    hud_app = _build_app()
    decision = hud_app.orchestrator.analyze_market(market_id, outcome_id=outcome_id)
    print(decision.model_dump_json(indent=2))


@app.command("run-daily-batch")
def run_daily_batch(market_id: str = "KXATLANTICSTORMS-26-N16") -> None:
    hud_app = _build_app()
    decision = hud_app.orchestrator.analyze_market(market_id)
    print(decision.model_dump_json(indent=2))


@app.command("rank-opportunities")
def rank_opportunities(market_id: str = "KXATLANTICSTORMS-26-N16") -> None:
    hud_app = _build_app()
    decision = hud_app.orchestrator.analyze_market(market_id)
    print(json.dumps({"market_id": market_id, "decision": decision.model_dump(mode="json")}, indent=2))


@app.command("run-evals")
def run_evals(output_file: Path | None = None) -> None:
    hud_app = _build_app()
    result = hud_app.env.run_scenario("full_pipeline_scenario", market_id="KXATLANTICSTORMS-26-N16")
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
        hud_app = _build_app()
        results = {
            "rules": hud_app.env.run_scenario("rules_scenario", market_id="KXATLANTICSTORMS-26-N16").score,
            "research": hud_app.env.run_scenario("research_scenario", market_id="KXATLANTICSTORMS-26-N16").score,
            "skeptic": hud_app.env.run_scenario("skeptic_scenario", market_id="KXATLANTICSTORMS-26-N16").score,
            "probability": hud_app.env.run_scenario("probability_scenario", market_id="KXATLANTICSTORMS-26-N16").score,
        }
        print(json.dumps({"status": "fallback_scenarios", "results": results}, indent=2))


@app.command("run_eval_suite")
def run_eval_suite(output_file: Path | None = None) -> None:
    hud_app = _build_app()
    outputs = {
        name: hud_app.env.run_scenario(name, market_id="KXATLANTICSTORMS-26-N16").model_dump(mode="json")
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
