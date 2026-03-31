from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from polymarket_ai.hud.environment import prediction_market_env
from polymarket_ai.hud.models import DecisionKind, RuleAnalysis
from polymarket_ai.hud.runtime import RUNTIME
from polymarket_ai.models import Market, RunRecord, TradeDecision


@prediction_market_env.tool(name="get_market_data", description="Fetch a normalized market by market_id.")
def get_market_data(market_id: str) -> Market:
    if RUNTIME.market_service is None:
        raise RuntimeError("HUD runtime market service is not configured.")
    stored = RUNTIME.market_service.get_market_data(market_id)
    return stored


@prediction_market_env.tool(name="search_web", description="Search for public sources relevant to the market.")
def search_web(query: str) -> list[str]:
    return [
        f"https://example.org/search?q={query}",
        "https://www.noaa.gov/",
    ]


@prediction_market_env.tool(name="fetch_source", description="Fetch and summarize a source document.")
def fetch_source(url: str) -> dict[str, str]:
    if RUNTIME.research_service is not None:
        summary = RUNTIME.research_service.fetch_source(url)
    else:
        summary = f"Retrieved source content from {url}"
    return {
        "url": url,
        "title": "Fetched source",
        "summary": summary,
    }


@prediction_market_env.tool(name="parse_rules", description="Parse the raw market rules into explicit criteria.")
def parse_rules(raw_rules: str) -> RuleAnalysis:
    parsed_rules = [line.strip("- ").strip() for line in raw_rules.splitlines() if line.strip()]
    if not parsed_rules:
        parsed_rules = [raw_rules.strip()]
    risks = []
    if "official" not in raw_rules.lower():
        risks.append("No explicit official resolution source was stated.")
    return RuleAnalysis(
        market_id="unknown",
        parsed_rules=parsed_rules,
        risks=risks,
        clarity_score=1.0 if parsed_rules else 0.0,
    )


@prediction_market_env.tool(name="compute_ev", description="Compute edge and EV in pure Python.")
def compute_ev(market_prob: float, fair_prob: float, fee_bps: int, slippage_bps: int) -> dict[str, float]:
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


@prediction_market_env.tool(name="save_run", description="Persist a run summary for later inspection.")
def save_run(run_payload: dict[str, object]) -> dict[str, object]:
    saved = dict(run_payload)
    saved["saved_at"] = datetime.now(tz=timezone.utc).isoformat()
    saved["saved"] = True
    if RUNTIME.run_repo is not None and "run_id" in saved and "market_id" in saved:
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
        RUNTIME.run_repo.save(
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


def new_run_id() -> str:
    return str(uuid4())
