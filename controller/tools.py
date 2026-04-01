from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from polymarket_ai.hud.app import HUDApplication, create_hud_app

app: HUDApplication = create_hud_app()
mcp = FastMCP(
    name="polymarket-ai-system",
    instructions=(
        "Paper-trading and research environment for Polymarket analysis. "
        "This deployment is research-only and must fail closed to NO_TRADE on uncertainty or tool failure."
    ),
)


@mcp.tool(name="analyze_market", description="Run the full orchestrator flow for a single market in paper mode.", task=True)
async def analyze_market(market_id: str, outcome_id: str = "yes") -> dict[str, Any]:
    decision = await asyncio.to_thread(app.orchestrator.analyze_market, market_id, outcome_id)
    return decision.model_dump(mode="json")


@mcp.tool(name="get_market_data", description="Fetch a normalized market by market_id.")
def get_market_data(market_id: str) -> dict[str, Any]:
    return app.runtime.market_service.get_market_data(market_id).model_dump(mode="json")


@mcp.tool(name="search_web", description="Search for public sources relevant to the market.")
def search_web(query: str) -> list[str]:
    return app.env.call_tool("search_web", query)


@mcp.tool(name="fetch_source", description="Fetch and summarize a source document.")
def fetch_source(url: str) -> dict[str, Any]:
    return app.env.call_tool("fetch_source", url)


@mcp.tool(name="parse_rules", description="Parse the raw market rules into explicit criteria.")
def parse_rules(raw_rules: str) -> dict[str, Any]:
    return app.env.call_tool("parse_rules", raw_rules).model_dump(mode="json")


@mcp.tool(name="compute_ev", description="Compute edge and EV in pure Python.")
def compute_ev(market_prob: float, fair_prob: float, fee_bps: int, slippage_bps: int) -> dict[str, Any]:
    return app.env.call_tool("compute_ev", market_prob, fair_prob, fee_bps, slippage_bps)


@mcp.tool(name="run_scenario", description="Run a named weighted eval scenario for a market.", task=True)
async def run_scenario(
    scenario_name: str,
    market_id: str,
    expected_decision: str | None = None,
    expected_edge_sign: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"market_id": market_id}
    if expected_decision is not None:
        kwargs["expected_decision"] = expected_decision
    if expected_edge_sign is not None:
        kwargs["expected_edge_sign"] = expected_edge_sign
    result = await asyncio.to_thread(app.env.run_scenario, scenario_name, **kwargs)
    return result.model_dump(mode="json")
