from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from polymarket_ai.hud.environment import EnvTool
from polymarket_ai.hud.models import DecisionKind, RuleAnalysis
from polymarket_ai.hud.runtime import HUDRuntime
from polymarket_ai.models import Market, RunRecord, TradeDecision


def compute_expected_value(
    market_prob: float,
    fair_prob: float,
    fee_bps: int,
    slippage_bps: int,
) -> dict[str, float]:
    cost = (fee_bps + slippage_bps) / 10000
    edge = fair_prob - market_prob
    expected_value = edge - cost
    return {
        "market_prob": market_prob,
        "fair_prob": fair_prob,
        "edge": edge,
        "expected_value": expected_value,
        "fee_and_slippage_cost": cost,
    }


def register_tools(env: object, runtime: HUDRuntime, orchestrator: object) -> None:
    registry = getattr(env, "tools", None)
    if not isinstance(registry, dict):
        registry = {}
        try:
            setattr(env, "tools", registry)
        except Exception:
            setattr(env, "_polymarket_tools", registry)

    @env.tool(name="get_market_data", description="Fetch a normalized market by market_id.")  # type: ignore[attr-defined]
    def get_market_data(market_id: str) -> Market:
        return runtime.market_service.get_market_data(market_id)
    registry["get_market_data"] = EnvTool(
        name="get_market_data",
        description="Fetch a normalized market by market_id.",
        handler=get_market_data,
    )

    @env.tool(name="search_web", description="Search for public sources relevant to the market.")  # type: ignore[attr-defined]
    def search_web(query: str) -> list[str]:
        return [
            f"https://example.org/search?q={query}",
            "https://www.noaa.gov/",
        ]
    registry["search_web"] = EnvTool(
        name="search_web",
        description="Search for public sources relevant to the market.",
        handler=search_web,
    )

    @env.tool(name="fetch_source", description="Fetch and summarize a source document.")  # type: ignore[attr-defined]
    def fetch_source(url: str) -> dict[str, str]:
        summary = runtime.research_service.fetch_source(url)
        return {
            "url": url,
            "title": "Fetched source",
            "summary": summary,
        }
    registry["fetch_source"] = EnvTool(
        name="fetch_source",
        description="Fetch and summarize a source document.",
        handler=fetch_source,
    )

    @env.tool(name="parse_rules", description="Parse the raw market rules into explicit criteria.")  # type: ignore[attr-defined]
    def parse_rules(raw_rules: str) -> RuleAnalysis:
        parsed_rules = [line.strip("- ").strip() for line in raw_rules.splitlines() if line.strip()]
        if not parsed_rules:
            parsed_rules = [raw_rules.strip()]
        risks: list[str] = []
        if "official" not in raw_rules.lower():
            risks.append("No explicit official resolution source was stated.")
        return RuleAnalysis(
            market_id="unknown",
            parsed_rules=parsed_rules,
            risks=risks,
            clarity_score=1.0 if parsed_rules else 0.0,
        )
    registry["parse_rules"] = EnvTool(
        name="parse_rules",
        description="Parse the raw market rules into explicit criteria.",
        handler=parse_rules,
    )

    @env.tool(name="compute_ev", description="Compute edge and EV in pure Python.")  # type: ignore[attr-defined]
    def compute_ev(market_prob: float, fair_prob: float, fee_bps: int, slippage_bps: int) -> dict[str, float]:
        return compute_expected_value(market_prob, fair_prob, fee_bps, slippage_bps)
    registry["compute_ev"] = EnvTool(
        name="compute_ev",
        description="Compute edge and EV in pure Python.",
        handler=compute_ev,
    )

    @env.tool(name="save_run", description="Persist a run summary for later inspection.")  # type: ignore[attr-defined]
    def save_run(run_payload: dict[str, object]) -> dict[str, object]:
        saved = dict(run_payload)
        saved["saved_at"] = datetime.now(tz=timezone.utc).isoformat()
        saved["saved"] = True
        if "run_id" in saved and "market_id" in saved:
            decision_payload = saved.get("final_decision")
            if isinstance(decision_payload, dict):
                final_decision = TradeDecision.model_validate(decision_payload)
            else:
                final_decision = TradeDecision(
                    run_id=str(saved["run_id"]),
                    market_id=str(saved["market_id"]),
                    market_prob=0.0,
                    fair_prob=0.0,
                    edge=0.0,
                    confidence=0.0,
                    decision=DecisionKind.NO_TRADE,
                    reasoning_summary="Saved by HUD tool.",
                    risks=[],
                    sources=[],
                    expected_value=0.0,
                    trace_id=str(saved.get("trace_id", uuid4())),
                )
            runtime.run_repo.save(
                RunRecord(
                    run_id=str(saved["run_id"]),
                    market_id=str(saved["market_id"]),
                    inputs=dict(saved.get("inputs", {"run_payload": saved})),
                    agent_outputs=dict(saved.get("agent_outputs", {})),
                    final_decision=final_decision,
                    started_at=datetime.fromisoformat(
                        str(saved.get("started_at", datetime.now(tz=timezone.utc).isoformat()))
                    ),
                    finished_at=datetime.fromisoformat(
                        str(saved.get("finished_at", datetime.now(tz=timezone.utc).isoformat()))
                    ),
                    trace_id=str(saved.get("trace_id", uuid4())),
                )
            )
        return saved
    registry["save_run"] = EnvTool(
        name="save_run",
        description="Persist a run summary for later inspection.",
        handler=save_run,
    )

    @env.tool(  # type: ignore[attr-defined]
        name="analyze_market",
        description="Run the full orchestrator flow for a single market in paper mode.",
    )
    def analyze_market(market_id: str, outcome_id: str = "yes") -> dict[str, object]:
        return orchestrator.analyze_market(market_id, outcome_id=outcome_id).model_dump(mode="json")
    registry["analyze_market"] = EnvTool(
        name="analyze_market",
        description="Run the full orchestrator flow for a single market in paper mode.",
        handler=analyze_market,
    )


def new_run_id() -> str:
    return str(uuid4())
