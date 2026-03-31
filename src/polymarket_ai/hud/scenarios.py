from __future__ import annotations

from datetime import datetime, timezone

from polymarket_ai.hud.agents import ProbabilityAgent, ResearchAgent, RulesAgent, SkepticAgent, final_decision
from polymarket_ai.hud.config import ModelRoute
from polymarket_ai.hud.environment import prediction_market_env
from polymarket_ai.hud.models import DecisionKind, ScenarioResult
from polymarket_ai.hud.tools import compute_ev, get_market_data, new_run_id, parse_rules, save_run, search_web
from polymarket_ai.models import ProbabilityAgentInput, ResearchAgentInput, RulesAgentInput, SkepticAgentInput


rules_agent = RulesAgent(
    name="RulesAgent",
    instructions="Parse resolution rules into explicit, testable criteria.",
    route=ModelRoute(tier="cheap", model="hud-lite", purpose="rules parsing"),
    tools=("parse_rules",),
)
research_agent = ResearchAgent(
    name="ResearchAgent",
    instructions="Collect supporting and opposing evidence with citations.",
    route=ModelRoute(tier="mid", model="hud-balanced", purpose="research synthesis"),
    tools=("search_web", "fetch_source"),
)
skeptic_agent = SkepticAgent(
    name="SkepticAgent",
    instructions="Challenge the thesis and surface failure modes.",
    route=ModelRoute(tier="mid", model="hud-balanced", purpose="bear case analysis"),
)
probability_agent = ProbabilityAgent(
    name="ProbabilityAgent",
    instructions="Estimate fair probability and determine tradeability.",
    route=ModelRoute(tier="high", model="hud-pro", purpose="probability synthesis"),
)


@prediction_market_env.scenario(name="research_scenario", description="Research agent boundary and evidence gathering.")
def research_scenario(market_id: str) -> ScenarioResult:
    market = get_market_data(market_id)
    sources = search_web(market.question)
    rules = rules_agent.run(RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes"))
    report = research_agent.run(
        ResearchAgentInput(trace_id=market_id, market=market, outcome_id="yes", rules_output=rules)
    )
    score = min(1.0, 0.3 + 0.2 * len(sources) + 0.4 * report.confidence)
    return ScenarioResult(
        name="research_scenario",
        output={"market_id": market.market_id, "sources": sources, "report": report.model_dump(mode="json")},
        score=score,
        notes=["Validated research boundary", "Output is structured and citation-oriented"],
    )


@prediction_market_env.scenario(name="rules_scenario", description="Rules agent boundary and rule parsing quality.")
def rules_scenario(market_id: str) -> ScenarioResult:
    market = get_market_data(market_id)
    parsed = parse_rules(market.rules.raw_rules)
    score = parsed.clarity_score
    return ScenarioResult(
        name="rules_scenario",
        output={"market_id": market.market_id, "rules": parsed.model_dump(mode="json")},
        score=score,
        notes=["Rules parsing is explicit", "Low ambiguity receives lower score"],
    )


@prediction_market_env.scenario(name="skeptic_scenario", description="Skeptic agent boundary and counter-argument quality.")
def skeptic_scenario(market_id: str) -> ScenarioResult:
    market = get_market_data(market_id)
    rules = rules_agent.run(RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes"))
    research = research_agent.run(
        ResearchAgentInput(trace_id=market_id, market=market, outcome_id="yes", rules_output=rules)
    )
    skeptic = skeptic_agent.run(
        SkepticAgentInput(
            trace_id=market_id,
            market=market,
            research_output=research,
            rules_output=rules,
        )
    )
    score = max(0.0, 1.0 - skeptic.confidence_penalty)
    return ScenarioResult(
        name="skeptic_scenario",
        output={"market_id": market.market_id, "skeptic": skeptic.model_dump(mode="json")},
        score=score,
        notes=["Bear case is explicit", "Failure modes are surfaced before probability scoring"],
    )


@prediction_market_env.scenario(name="probability_scenario", description="Probability agent boundary and EV computation.")
def probability_scenario(market_id: str) -> ScenarioResult:
    market = get_market_data(market_id)
    rules = rules_agent.run(RulesAgentInput(trace_id=market_id, market=market, outcome_id="yes"))
    research = research_agent.run(
        ResearchAgentInput(trace_id=market_id, market=market, outcome_id="yes", rules_output=rules)
    )
    skeptic = skeptic_agent.run(
        SkepticAgentInput(
            trace_id=market_id,
            market=market,
            research_output=research,
            rules_output=rules,
        )
    )
    probability = probability_agent.run(
        ProbabilityAgentInput(
            trace_id=market_id,
            market=market,
            outcome_id="yes",
            rules_output=rules,
            research_output=research,
            skeptic_output=skeptic,
        )
    )
    ev = compute_ev(probability.market_prob, probability.fair_prob, 150, 50)
    score = max(0.0, min(1.0, probability.confidence + (1.0 if ev["expected_value"] > 0 else 0.0) / 2))
    return ScenarioResult(
        name="probability_scenario",
        output={
            "market_id": market.market_id,
            "probability": probability.model_dump(mode="json"),
            "ev": ev,
        },
        score=score,
        notes=["Probability estimate is structured", "EV is computed in pure Python"],
    )


@prediction_market_env.scenario(name="full_pipeline_scenario", description="Full hierarchical agent pipeline.")
def full_pipeline_scenario(market_id: str) -> ScenarioResult:
    started_at = datetime.now(tz=timezone.utc)
    run_id = new_run_id()
    market = get_market_data(market_id)
    rules = rules_agent.run(RulesAgentInput(trace_id=run_id, market=market, outcome_id="yes"))
    research = research_agent.run(
        ResearchAgentInput(trace_id=run_id, market=market, outcome_id="yes", rules_output=rules)
    )
    skeptic = skeptic_agent.run(
        SkepticAgentInput(
            trace_id=run_id,
            market=market,
            research_output=research,
            rules_output=rules,
        )
    )
    probability = probability_agent.run(
        ProbabilityAgentInput(
            trace_id=run_id,
            market=market,
            outcome_id="yes",
            rules_output=rules,
            research_output=research,
            skeptic_output=skeptic,
        )
    )
    ev = compute_ev(probability.market_prob, probability.fair_prob, 150, 50)
    final_kind = probability.decision
    if probability.confidence < 0.65 or ev["edge"] < 0.05:
        final_kind = DecisionKind.NO_TRADE
    elif probability.confidence < 0.75:
        final_kind = DecisionKind.WATCHLIST
    decision = final_decision(
        run_id=run_id,
        trace_id=run_id,
        estimate=probability.model_copy(update={"decision": final_kind, "expected_value": ev["expected_value"]}),
    ).model_copy(
        update={
            "agent_outputs": {
                "rules": rules.model_dump(mode="json"),
                "research": research.model_dump(mode="json"),
                "skeptic": skeptic.model_dump(mode="json"),
                "probability": probability.model_dump(mode="json"),
            }
        }
    )
    saved = save_run(
        {
            "run_id": run_id,
            "trace_id": run_id,
            "market_id": market.market_id,
            "final_decision": decision.model_dump(mode="json"),
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    )
    score = max(0.0, min(1.0, decision.confidence + (1.0 if decision.decision != "NO_TRADE" else 0.0) / 2))
    return ScenarioResult(
        name="full_pipeline_scenario",
        output={
            "run_id": run_id,
            "market_id": market.market_id,
            "rules": rules.model_dump(mode="json"),
            "research": research.model_dump(mode="json"),
            "skeptic": skeptic.model_dump(mode="json"),
            "probability": probability.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json"),
            "saved_run": saved,
        },
        score=score,
        notes=["Orchestrator delegates to narrow subagents", "Structured outputs survive the entire path"],
    )
