import asyncio

from controller.tools import app, mcp


def test_controller_builds_hud_app() -> None:
    assert app.orchestrator is not None
    assert mcp is not None
    assert mcp.name == "polymarket-ai-system"


def test_controller_exposes_expected_tools_only() -> None:
    tools = asyncio.run(mcp.list_tools())
    tool_names = {tool.name for tool in tools}
    assert "hud_readiness" not in tool_names
    assert tool_names == {
        "analyze_market",
        "get_market_data",
        "search_web",
        "fetch_source",
        "parse_rules",
        "compute_ev",
        "run_scenario",
    }
