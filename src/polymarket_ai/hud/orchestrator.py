from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from polymarket_ai.hud.agents import ProbabilityAgent, ResearchAgent, RulesAgent, SkepticAgent, final_decision
from polymarket_ai.hud.config import HUDSettings, ModelRoute
from polymarket_ai.hud.models import DecisionKind, FinalDecision
from polymarket_ai.hud.runtime import RUNTIME
from polymarket_ai.hud.tools import compute_ev, get_market_data, save_run
from polymarket_ai.models import ProbabilityAgentInput, ResearchAgentInput, RulesAgentInput, RunRecord, SkepticAgentInput
from polymarket_ai.reliability.circuit_breaker import CircuitBreaker
from polymarket_ai.reliability.retry import RetryPolicy, retry


class PredictionMarketOrchestrator:
    def __init__(self, settings: HUDSettings | None = None) -> None:
        self.settings = settings or HUDSettings()
        self.rules_agent = RulesAgent(
            name="RulesAgent",
            instructions="Parse exact resolution rules into concrete criteria.",
            route=ModelRoute(tier="cheap", model=self.settings.cheap_model, purpose="rules parsing"),
            tools=("parse_rules",),
        )
        self.research_agent = ResearchAgent(
            name="ResearchAgent",
            instructions="Gather supporting and opposing evidence with citations.",
            route=ModelRoute(tier="mid", model=self.settings.mid_tier_model, purpose="research synthesis"),
            tools=("search_web", "fetch_source"),
        )
        self.skeptic_agent = SkepticAgent(
            name="SkepticAgent",
            instructions="Challenge the thesis before any recommendation is made.",
            route=ModelRoute(tier="mid", model=self.settings.mid_tier_model, purpose="skeptic pass"),
        )
        self.probability_agent = ProbabilityAgent(
            name="ProbabilityAgent",
            instructions="Estimate fair probability and decision quality.",
            route=ModelRoute(tier="high", model=self.settings.high_capability_model, purpose="probability synthesis"),
        )
        self.breaker = CircuitBreaker()

    @retry(RetryPolicy(max_attempts=3, backoff_seconds=0.2))
    def analyze_market(self, market_id: str, outcome_id: str = "yes") -> FinalDecision:
        run_id = str(uuid4())
        trace_id = str(uuid4())
        if not self.breaker.allow():
            return self._fallback(market_id, run_id, trace_id, "Circuit breaker open; defaulting to no trade.")
        started_at = datetime.now(tz=timezone.utc)
        try:
            market = get_market_data(market_id)
            rules = self.rules_agent.run(
                RulesAgentInput(trace_id=trace_id, market=market, outcome_id=outcome_id)
            )
            research = self.research_agent.run(
                ResearchAgentInput(
                    trace_id=trace_id,
                    market=market,
                    outcome_id=outcome_id,
                    rules_output=rules,
                )
            )
            skeptic = self.skeptic_agent.run(
                SkepticAgentInput(
                    trace_id=trace_id,
                    market=market,
                    research_output=research,
                    rules_output=rules,
                )
            )
            probability = self.probability_agent.run(
                ProbabilityAgentInput(
                    trace_id=trace_id,
                    market=market,
                    outcome_id=outcome_id,
                    rules_output=rules,
                    research_output=research,
                    skeptic_output=skeptic,
                )
            )
            ev = compute_ev(
                probability.market_prob,
                probability.fair_prob,
                self.settings.fee_bps,
                self.settings.slippage_bps,
            )
            decision = DecisionKind.NO_TRADE
            if rules.clarity_score >= 0.5 and probability.confidence >= self.settings.min_confidence and ev["edge"] >= self.settings.min_edge:
                decision = DecisionKind.PAPER_TRADE
            elif probability.confidence >= self.settings.watchlist_confidence and ev["edge"] > 0:
                decision = DecisionKind.WATCHLIST

            final = final_decision(
                run_id=run_id,
                trace_id=trace_id,
                estimate=probability.model_copy(update={"decision": decision, "expected_value": ev["expected_value"]}),
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
            if RUNTIME.trade_repo is not None:
                RUNTIME.trade_repo.save(final)
            save_run(
                {
                    "run_id": run_id,
                    "trace_id": trace_id,
                    "market_id": market.market_id,
                    "inputs": {"market_id": market_id, "outcome_id": outcome_id},
                    "agent_outputs": final.agent_outputs or {},
                    "final_decision": final.model_dump(mode="json"),
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            )
            self.breaker.record_success()
            return final
        except Exception:
            self.breaker.record_failure()
            return self._fallback(market_id, run_id, trace_id, "Orchestrator fallback after agent failure.")

    def _fallback(self, market_id: str, run_id: str, trace_id: str, message: str) -> FinalDecision:
        return FinalDecision(
            market_id=market_id,
            market_prob=0.0,
            fair_prob=0.0,
            edge=0.0,
            confidence=0.0,
            decision=DecisionKind.NO_TRADE,
            reasoning_summary=message,
            risks=["fallback engaged"],
            sources=[],
            expected_value=0.0,
            run_id=run_id,
            trace_id=trace_id,
            snapshot_as_of=None,
            agent_outputs={},
        )
