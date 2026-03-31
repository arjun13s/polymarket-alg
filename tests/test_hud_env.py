from polymarket_ai.hud.environment import prediction_market_env
from polymarket_ai.hud.models import DecisionKind
from polymarket_ai.hud.orchestrator import PredictionMarketOrchestrator
from polymarket_ai.hud.scenarios import full_pipeline_scenario, probability_scenario, research_scenario, rules_scenario, skeptic_scenario


def test_prediction_market_env_registers_tools_and_scenarios() -> None:
    assert "get_market_data" in prediction_market_env.tools
    assert "search_web" in prediction_market_env.tools
    assert "parse_rules" in prediction_market_env.tools
    assert "compute_ev" in prediction_market_env.tools
    assert "save_run" in prediction_market_env.tools
    assert "research_scenario" in prediction_market_env.scenarios
    assert "full_pipeline_scenario" in prediction_market_env.scenarios


def test_full_pipeline_scenario_returns_structured_output() -> None:
    result = prediction_market_env.run_scenario("full_pipeline_scenario", market_id="atlantic_hurricanes_over_15_2026")
    payload = result.model_dump(mode="json")
    assert payload["name"] == "full_pipeline_scenario"
    assert "decision" in payload["output"]
    assert isinstance(payload["score"], float)


def test_orchestrator_falls_back_to_no_trade_for_unknown_market() -> None:
    decision = PredictionMarketOrchestrator().analyze_market("missing_market_id")
    assert decision.decision == DecisionKind.NO_TRADE
    assert decision.reasoning_summary
