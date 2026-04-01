from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from polymarket_ai.hud.agents import ProbabilityAgent, ResearchAgent, RulesAgent, SkepticAgent, final_decision
from polymarket_ai.hud.config import HUDSettings, build_model_routes
from polymarket_ai.hud.models import DecisionKind, FinalDecision
from polymarket_ai.hud.runtime import HUDRuntime
from polymarket_ai.hud.tools import compute_expected_value
from polymarket_ai.models import (
    ProbabilityAgentInput,
    ResearchAgentInput,
    RulesAgentInput,
    RunRecord,
    SkepticAgentInput,
    TradeDecision,
)
from polymarket_ai.reliability.circuit_breaker import CircuitBreaker
from polymarket_ai.reliability.retry import RetryPolicy, retry


@dataclass(slots=True)
class AgentSuite:
    rules: RulesAgent
    research: ResearchAgent
    skeptic: SkepticAgent
    probability: ProbabilityAgent


class PredictionMarketOrchestrator:
    def __init__(
        self,
        runtime: HUDRuntime,
        settings: HUDSettings | None = None,
        agents: AgentSuite | None = None,
    ) -> None:
        self.runtime = runtime
        self.settings = settings or runtime.settings
        self.file_config = self.settings.load_file_config()
        self.routes = build_model_routes(self.settings)
        self.agents = agents or self._build_default_agents()
        self.breaker = CircuitBreaker()

    def _build_default_agents(self) -> AgentSuite:
        return AgentSuite(
            rules=RulesAgent(
                name="RulesAgent",
                instructions="Parse exact resolution rules into concrete criteria.",
                route=self.routes["rules"],
                tools=self.routes["rules"].allowed_tools,
            ),
            research=ResearchAgent(
                name="ResearchAgent",
                instructions="Gather supporting and opposing evidence with citations.",
                route=self.routes["research"],
                tools=self.routes["research"].allowed_tools,
            ),
            skeptic=SkepticAgent(
                name="SkepticAgent",
                instructions="Challenge the thesis before any recommendation is made.",
                route=self.routes["skeptic"],
                tools=self.routes["skeptic"].allowed_tools,
            ),
            probability=ProbabilityAgent(
                name="ProbabilityAgent",
                instructions="Estimate fair probability and decision quality.",
                route=self.routes["probability"],
                tools=self.routes["probability"].allowed_tools,
            ),
        )

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def analyze_market(self, market_id: str, outcome_id: str = "yes") -> FinalDecision:
        run_id = str(uuid4())
        trace_id = str(uuid4())
        started_at = datetime.now(tz=timezone.utc)
        if not self.breaker.allow():
            final = self._fallback(
                market_id=market_id,
                run_id=run_id,
                trace_id=trace_id,
                message="Circuit breaker open; defaulting to NO_TRADE.",
            )
            self._persist_fallback_safely(
                final, started_at, {"market_id": market_id, "outcome_id": outcome_id}, {}
            )
            return final

        agent_outputs: dict[str, object] = {}
        try:
            market = self.runtime.market_service.get_market_data(market_id)
            rules = self.agents.rules.run(
                RulesAgentInput(trace_id=trace_id, market=market, outcome_id=outcome_id)
            )
            agent_outputs["rules"] = rules.model_dump(mode="json")

            research = self.agents.research.run(
                ResearchAgentInput(
                    trace_id=trace_id,
                    market=market,
                    outcome_id=outcome_id,
                    rules_output=rules,
                )
            )
            agent_outputs["research"] = research.model_dump(mode="json")

            skeptic = self.agents.skeptic.run(
                SkepticAgentInput(
                    trace_id=trace_id,
                    market=market,
                    research_output=research,
                    rules_output=rules,
                )
            )
            agent_outputs["skeptic"] = skeptic.model_dump(mode="json")

            probability = self.agents.probability.run(
                ProbabilityAgentInput(
                    trace_id=trace_id,
                    market=market,
                    outcome_id=outcome_id,
                    rules_output=rules,
                    research_output=research,
                    skeptic_output=skeptic,
                )
            )
            agent_outputs["probability"] = probability.model_dump(mode="json")

            ev = compute_expected_value(
                probability.market_prob,
                probability.fair_prob,
                self.settings.default_fee_bps,
                self.settings.default_slippage_bps,
            )
            decision = self._apply_trade_filters(
                market_status=market.status.value,
                rule_clarity=rules.clarity_score,
                confidence=probability.confidence,
                edge=ev["edge"],
                expected_value=ev["expected_value"],
            )
            final = final_decision(
                run_id=run_id,
                trace_id=trace_id,
                estimate=probability.model_copy(
                    update={
                        "decision": decision,
                        "expected_value": ev["expected_value"],
                        "edge": ev["edge"],
                    }
                ),
            ).model_copy(update={"agent_outputs": agent_outputs})
            self._persist_run(
                final,
                started_at,
                {"market_id": market_id, "outcome_id": outcome_id},
                agent_outputs,
            )
            self.breaker.record_success()
            return final
        except Exception as exc:
            self.breaker.record_failure()
            final = self._fallback(
                market_id=market_id,
                run_id=run_id,
                trace_id=trace_id,
                message=f"Orchestrator fallback after {exc.__class__.__name__}: {exc}",
            )
            self._persist_fallback_safely(
                final, started_at, {"market_id": market_id, "outcome_id": outcome_id}, agent_outputs
            )
            return final

    def _apply_trade_filters(
        self,
        market_status: str,
        rule_clarity: float,
        confidence: float,
        edge: float,
        expected_value: float,
    ) -> DecisionKind:
        if market_status != "open":
            return DecisionKind.NO_TRADE
        if rule_clarity < 0.5:
            return DecisionKind.NO_TRADE
        if confidence < self.file_config.pricing.min_confidence:
            return DecisionKind.NO_TRADE
        if edge < self.file_config.pricing.min_edge:
            return DecisionKind.NO_TRADE
        if expected_value <= 0:
            return DecisionKind.NO_TRADE
        if confidence < self.file_config.pricing.paper_trade_confidence:
            return DecisionKind.WATCHLIST
        return DecisionKind.PAPER_TRADE

    def _persist_run(
        self,
        final: FinalDecision,
        started_at: datetime,
        inputs: dict[str, object],
        agent_outputs: dict[str, object],
    ) -> None:
        self.runtime.run_repo.save(
            RunRecord(
                run_id=final.run_id,
                market_id=final.market_id,
                inputs=inputs,
                agent_outputs=agent_outputs,
                final_decision=self._to_trade_decision(final),
                started_at=started_at,
                finished_at=datetime.now(tz=timezone.utc),
                trace_id=final.trace_id,
            )
        )

    def _persist_fallback_safely(
        self,
        final: FinalDecision,
        started_at: datetime,
        inputs: dict[str, object],
        agent_outputs: dict[str, object],
    ) -> None:
        try:
            self._persist_run(final, started_at, inputs, agent_outputs)
        except Exception:
            return

    def _to_trade_decision(self, final: FinalDecision) -> TradeDecision:
        return TradeDecision(
            run_id=final.run_id,
            market_id=final.market_id,
            market_prob=final.market_prob,
            fair_prob=final.fair_prob,
            edge=final.edge,
            confidence=final.confidence,
            decision=final.decision.value,
            reasoning_summary=final.reasoning_summary,
            risks=final.risks,
            sources=final.sources,
            expected_value=final.expected_value,
            trace_id=final.trace_id,
            snapshot_at=final.snapshot_as_of,
        )

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
