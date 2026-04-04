from polymarket_ai.hud.app import create_hud_app
from polymarket_ai.hud.models import DecisionKind
from polymarket_ai.hud.orchestrator import PredictionMarketOrchestrator


def test_prediction_market_env_registers_tools_and_scenarios() -> None:
    hud_app = create_hud_app()
    assert "get_market_data" in hud_app.env.tools
    assert "search_web" in hud_app.env.tools
    assert "parse_rules" in hud_app.env.tools
    assert "compute_ev" in hud_app.env.tools
    assert "save_run" in hud_app.env.tools
    assert "research_scenario" in hud_app.env.scenarios
    assert "full_pipeline_scenario" in hud_app.env.scenarios


def test_full_pipeline_scenario_returns_structured_output() -> None:
    hud_app = create_hud_app()
    result = hud_app.env.run_scenario("full_pipeline_scenario", market_id="KXATLANTICSTORMS-26-N16")
    payload = result.model_dump(mode="json")
    assert payload["name"] == "full_pipeline_scenario"
    assert "decision" in payload["output"]
    assert isinstance(payload["score"], float)


def test_orchestrator_falls_back_to_no_trade_for_unknown_market() -> None:
    hud_app = create_hud_app()
    decision = PredictionMarketOrchestrator(runtime=hud_app.runtime, settings=hud_app.settings).analyze_market(
        "missing_market_id"
    )
    assert decision.decision == DecisionKind.NO_TRADE
    assert decision.reasoning_summary
