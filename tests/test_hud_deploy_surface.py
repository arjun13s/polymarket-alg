from polymarket_ai.hud.app import create_hud_app


def test_create_hud_app_builds_single_runtime_surface() -> None:
    hud_app = create_hud_app()
    assert hud_app.orchestrator.runtime is hud_app.runtime
    assert "analyze_market" in hud_app.env.tools
    assert "full_pipeline_scenario" in hud_app.env.scenarios


def test_hud_environment_registers_expected_core_tools() -> None:
    hud_app = create_hud_app()
    assert "analyze_market" in hud_app.env.tools
    assert "full_pipeline_scenario" in hud_app.env.scenarios
    assert "hud_readiness" not in hud_app.env.tools
