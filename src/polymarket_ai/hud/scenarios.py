from __future__ import annotations

from polymarket_ai.hud.environment import ScenarioSpec
from polymarket_ai.hud.models import DecisionKind, ScenarioResult
from polymarket_ai.hud.orchestrator import PredictionMarketOrchestrator
from polymarket_ai.hud.runtime import HUDRuntime
from polymarket_ai.hud.tools import compute_expected_value
from polymarket_ai.infra.config import Settings
from polymarket_ai.models import ProbabilityAgentInput, ResearchAgentInput, RulesAgentInput, SkepticAgentInput


def register_scenarios(
    env: object,
    runtime: HUDRuntime,
    orchestrator: PredictionMarketOrchestrator,
    settings: Settings,
) -> None:
    registry = getattr(env, "scenarios", None)
    if not isinstance(registry, dict):
        registry = {}
        try:
            setattr(env, "scenarios", registry)
        except Exception:
            setattr(env, "_polymarket_scenarios", registry)

    @env.scenario(  # type: ignore[attr-defined]
        name="research_scenario",
        description="Research agent boundary and evidence gathering.",
    )
    def research_scenario(market_id: str) -> ScenarioResult:
        market = runtime.market_service.get_market_data(market_id)
        rules = orchestrator.agents.rules.run(
            RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes")
        )
        report = orchestrator.agents.research.run(
            ResearchAgentInput(trace_id=market_id, market=market, outcome_id="yes", rules_output=rules)
        )
        score = _weighted_score(
            decision_quality=min(1.0, report.confidence + 0.2),
            calibration=report.confidence,
            ev_realism=1.0 if report.sources else 0.0,
        )
        return ScenarioResult(
            name="research_scenario",
            output={"market_id": market.market_id, "report": report.model_dump(mode="json")},
            score=score,
            notes=["Validated research boundary", "Output is structured and citation-oriented"],
            component_scores={
                "decision_quality": min(1.0, report.confidence + 0.2),
                "calibration": report.confidence,
                "ev_realism": 1.0 if report.sources else 0.0,
            },
        )
    registry["research_scenario"] = ScenarioSpec(
        name="research_scenario",
        description="Research agent boundary and evidence gathering.",
        handler=research_scenario,
    )

    @env.scenario(name="rules_scenario", description="Rules agent boundary and rule parsing quality.")  # type: ignore[attr-defined]
    def rules_scenario(market_id: str) -> ScenarioResult:
        market = runtime.market_service.get_market_data(market_id)
        rules = orchestrator.agents.rules.run(
            RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes")
        )
        score = _weighted_score(
            decision_quality=rules.clarity_score,
            calibration=rules.clarity_score,
            ev_realism=1.0 if not rules.risks else 0.6,
        )
        return ScenarioResult(
            name="rules_scenario",
            output={"market_id": market.market_id, "rules": rules.model_dump(mode="json")},
            score=score,
            notes=["Rules parsing is explicit", "Low ambiguity receives lower score"],
            component_scores={
                "decision_quality": rules.clarity_score,
                "calibration": rules.clarity_score,
                "ev_realism": 1.0 if not rules.risks else 0.6,
            },
        )
    registry["rules_scenario"] = ScenarioSpec(
        name="rules_scenario",
        description="Rules agent boundary and rule parsing quality.",
        handler=rules_scenario,
    )

    @env.scenario(name="skeptic_scenario", description="Skeptic agent boundary and counter-argument quality.")  # type: ignore[attr-defined]
    def skeptic_scenario(market_id: str) -> ScenarioResult:
        market = runtime.market_service.get_market_data(market_id)
        rules = orchestrator.agents.rules.run(
            RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes")
        )
        research = orchestrator.agents.research.run(
            ResearchAgentInput(trace_id=market_id, market=market, outcome_id="yes", rules_output=rules)
        )
        skeptic = orchestrator.agents.skeptic.run(
            SkepticAgentInput(
                trace_id=market_id,
                market=market,
                research_output=research,
                rules_output=rules,
            )
        )
        score = _weighted_score(
            decision_quality=max(0.0, 1.0 - skeptic.confidence_penalty),
            calibration=max(0.0, 1.0 - skeptic.confidence_penalty),
            ev_realism=1.0 if skeptic.failure_modes else 0.0,
        )
        return ScenarioResult(
            name="skeptic_scenario",
            output={"market_id": market.market_id, "skeptic": skeptic.model_dump(mode="json")},
            score=score,
            notes=["Bear case is explicit", "Failure modes are surfaced before probability scoring"],
            component_scores={
                "decision_quality": max(0.0, 1.0 - skeptic.confidence_penalty),
                "calibration": max(0.0, 1.0 - skeptic.confidence_penalty),
                "ev_realism": 1.0 if skeptic.failure_modes else 0.0,
            },
        )
    registry["skeptic_scenario"] = ScenarioSpec(
        name="skeptic_scenario",
        description="Skeptic agent boundary and counter-argument quality.",
        handler=skeptic_scenario,
    )

    @env.scenario(name="probability_scenario", description="Probability agent boundary and EV computation.")  # type: ignore[attr-defined]
    def probability_scenario(market_id: str) -> ScenarioResult:
        market = runtime.market_service.get_market_data(market_id)
        rules = orchestrator.agents.rules.run(
            RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes")
        )
        research = orchestrator.agents.research.run(
            ResearchAgentInput(trace_id=market_id, market=market, outcome_id="yes", rules_output=rules)
        )
        skeptic = orchestrator.agents.skeptic.run(
            SkepticAgentInput(
                trace_id=market_id,
                market=market,
                research_output=research,
                rules_output=rules,
            )
        )
        probability = orchestrator.agents.probability.run(
            ProbabilityAgentInput(
                trace_id=market_id,
                market=market,
                outcome_id="yes",
                rules_output=rules,
                research_output=research,
                skeptic_output=skeptic,
            )
        )
        ev = compute_expected_value(
            probability.market_prob,
            probability.fair_prob,
            settings.default_fee_bps,
            settings.default_slippage_bps,
        )
        component_scores = {
            "decision_quality": 1.0 if probability.reasoning_summary else 0.0,
            "calibration": max(0.0, 1.0 - abs(probability.fair_prob - probability.market_prob)),
            "ev_realism": 1.0 if ev["expected_value"] > 0 else 0.2,
        }
        return ScenarioResult(
            name="probability_scenario",
            output={
                "market_id": market.market_id,
                "probability": probability.model_dump(mode="json"),
                "ev": ev,
            },
            score=_weighted_score(**component_scores),
            notes=["Probability estimate is structured", "EV is computed in pure Python"],
            component_scores=component_scores,
        )
    registry["probability_scenario"] = ScenarioSpec(
        name="probability_scenario",
        description="Probability agent boundary and EV computation.",
        handler=probability_scenario,
    )

    @env.scenario(name="full_pipeline_scenario", description="Full hierarchical agent pipeline.")  # type: ignore[attr-defined]
    def full_pipeline_scenario(
        market_id: str,
        expected_decision: str | None = None,
        expected_edge_sign: str | None = None,
    ) -> ScenarioResult:
        final = orchestrator.analyze_market(market_id, outcome_id="yes")
        component_scores = {
            "decision_quality": _decision_quality(final.decision, expected_decision),
            "calibration": max(0.0, 1.0 - abs(final.fair_prob - final.market_prob)),
            "ev_realism": _ev_realism(final.edge, expected_edge_sign, final.decision),
        }
        return ScenarioResult(
            name="full_pipeline_scenario",
            output={"market_id": market_id, "decision": final.model_dump(mode="json")},
            score=_weighted_score(**component_scores),
            notes=[
                "Orchestrator delegates to narrow subagents",
                "Structured outputs survive the entire path",
            ],
            component_scores=component_scores,
        )
    registry["full_pipeline_scenario"] = ScenarioSpec(
        name="full_pipeline_scenario",
        description="Full hierarchical agent pipeline.",
        handler=full_pipeline_scenario,
    )


def _weighted_score(decision_quality: float, calibration: float, ev_realism: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            (decision_quality * 0.45) + (calibration * 0.35) + (ev_realism * 0.20),
        ),
    )


def _decision_quality(actual: DecisionKind, expected_decision: str | None) -> float:
    if expected_decision is None:
        return 1.0 if actual in {DecisionKind.NO_TRADE, DecisionKind.WATCHLIST, DecisionKind.PAPER_TRADE} else 0.0
    return 1.0 if actual.value == expected_decision else 0.0


def _ev_realism(edge: float, expected_edge_sign: str | None, decision: DecisionKind) -> float:
    if expected_edge_sign == "positive":
        return 1.0 if edge > 0 else 0.0
    if expected_edge_sign == "negative":
        return 1.0 if edge <= 0 else 0.0
    if decision == DecisionKind.PAPER_TRADE:
        return 1.0 if edge > 0 else 0.0
    return 0.8 if edge <= 0 else 0.6
