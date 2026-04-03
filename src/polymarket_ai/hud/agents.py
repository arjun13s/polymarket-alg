from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Generic, TypeVar

from polymarket_ai.hud.config import ModelRoute
from polymarket_ai.hud.models import (
    DecisionKind,
    FinalDecision,
    ProbabilityOutput,
    ResearchOutput,
    RuleAnalysis,
    SkepticOutput,
)
from polymarket_ai.models import ProbabilityAgentInput, ResearchAgentInput, RulesAgentInput, SkepticAgentInput

I = TypeVar("I")
O = TypeVar("O")


@dataclass(slots=True)
class AgentTrace:
    agent_name: str
    instructions: str
    started_at: datetime
    finished_at: datetime
    notes: list[str]
    model: str
    tools: list[str]


@dataclass(slots=True)
class AgentTool(Generic[I, O]):
    name: str
    instructions: str
    route: ModelRoute
    tools: tuple[str, ...] = ()

    def run(self, payload: I) -> O:  # pragma: no cover
        raise NotImplementedError

    def _trace(self, notes: list[str]) -> dict[str, object]:
        now = datetime.now(tz=timezone.utc)
        return asdict(
            AgentTrace(
                agent_name=self.name,
                instructions=self.instructions,
                started_at=now,
                finished_at=now,
                notes=notes,
                model=self.route.model,
                tools=list(self.tools),
            )
        )


class RulesAgent(AgentTool[RulesAgentInput, RuleAnalysis]):
    def run(self, payload: RulesAgentInput) -> RuleAnalysis:
        parsed = payload.market.rules.parsed_resolution_criteria or [payload.market.rules.raw_rules]
        risks: list[str] = []
        if not payload.market.rules.raw_rules.strip():
            risks.append("Missing raw rules text.")
        if not parsed:
            risks.append("No parsed rule criteria were found.")
        if "official" not in payload.market.rules.raw_rules.lower():
            risks.append("No explicit official resolution source found.")
        clarity = 1.0 if parsed else 0.0
        return RuleAnalysis(
            market_id=payload.market.market_id,
            parsed_rules=parsed,
            risks=risks,
            clarity_score=clarity,
            trace=self._trace(["Parsed resolution rules into explicit criteria."]),
        )


class ResearchAgent(AgentTool[ResearchAgentInput, ResearchOutput]):
    def run(self, payload: ResearchAgentInput) -> ResearchOutput:
        market = payload.market
        rules = payload.rules_output
        sources = [
            market.rules.source_url.unicode_string() if market.rules.source_url else "https://gamma-api.polymarket.com",
            "https://data-api.polymarket.com/trades",
        ]
        supporting_points = [
            f"Market liquidity is {market.liquidity:.2f} with 24h volume {market.volume_24h:.2f} in category {market.category}.",
            f"Recent Data API flow shows {market.recent_trade_count} trades and {market.recent_trade_volume:.2f} units of matched activity.",
            f"Rules are explicit enough to support a testable thesis in {market.market_id}.",
        ]
        opposing_points = [
            "The same public evidence may already be priced into the market.",
            "A narrow resolution interpretation could invalidate the thesis.",
        ]
        if market.last_activity_at is not None:
            supporting_points.append(
                f"Latest market activity timestamp from Data API: {market.last_activity_at.isoformat()}."
            )
        risks = list(rules.risks) + [
            "Evidence quality remains sensitive to source freshness.",
            f"Gamma/Data market snapshot may still lag if cache TTL is long; spread={market.spread}.",
        ]
        confidence = 0.72 if rules.clarity_score >= 0.5 else 0.45
        return ResearchOutput(
            market_id=market.market_id,
            summary="Collected support/opposition and market microstructure context from Gamma/Data API payloads.",
            sources=sources,
            supporting_points=supporting_points,
            opposing_points=opposing_points,
            risks=risks,
            confidence=confidence,
            trace=self._trace(["Gathered supporting and opposing evidence."]),
        )


class SkepticAgent(AgentTool[SkepticAgentInput, SkepticOutput]):
    def run(self, payload: SkepticAgentInput) -> SkepticOutput:
        market = payload.market
        research = payload.research_output
        counter_arguments = [
            "The crowd may already incorporate the same public evidence.",
            "High-attention markets are often harder to beat than they appear.",
        ]
        failure_modes = [
            "Resolution-rule interpretation may still be wrong.",
            "The evidence set may be stale or insufficiently authoritative.",
        ]
        if market.recent_trade_count >= 50 or market.attention_score >= 0.75:
            counter_arguments.append(
                "Recent Data API trade flow and attention are elevated, which raises crowd-efficiency risk."
            )
        if market.spread is not None and market.spread >= 0.05:
            failure_modes.append("Wide spread may erase the apparent edge before execution.")
        if research.confidence < 0.6:
            failure_modes.append("Low research confidence increases false-positive risk.")
        confidence_penalty = 0.2 if market.attention_score < 0.5 else 0.35
        return SkepticOutput(
            market_id=market.market_id,
            counter_arguments=counter_arguments,
            failure_modes=failure_modes,
            confidence_penalty=confidence_penalty,
            trace=self._trace(["Constructed explicit bear case and failure modes."]),
        )


class ProbabilityAgent(AgentTool[ProbabilityAgentInput, ProbabilityOutput]):
    def run(self, payload: ProbabilityAgentInput) -> ProbabilityOutput:
        market = payload.market
        research = payload.research_output
        rules = payload.rules_output
        skeptic = payload.skeptic_output
        target_outcome = next(
            (outcome for outcome in market.outcomes if outcome.outcome_id == payload.outcome_id),
            None,
        )
        market_prob = (
            target_outcome.price
            if target_outcome is not None
            else market.last_price or market.best_ask or market.best_bid or 0.5
        )
        fair_prob = min(
            0.99,
            max(
                0.01,
                market_prob
                + (research.confidence * 0.18)
                - (skeptic.confidence_penalty * 0.08)
                - min(0.03, market.attention_score * 0.02),
            ),
        )
        edge = fair_prob - market_prob
        confidence = max(0.0, min(1.0, research.confidence - skeptic.confidence_penalty))
        expected_value = edge - 0.02
        decision = DecisionKind.PAPER_TRADE if confidence >= 0.65 and edge >= 0.05 else DecisionKind.WATCHLIST
        if rules.clarity_score < 0.5:
            decision = DecisionKind.NO_TRADE
        return ProbabilityOutput(
            market_id=market.market_id,
            market_prob=market_prob,
            fair_prob=fair_prob,
            edge=edge,
            confidence=confidence,
            expected_value=expected_value,
            decision=decision,
            reasoning_summary="Estimated fair probability using research strength, rule clarity, and skeptic penalty.",
            risks=research.risks + skeptic.failure_modes,
            sources=research.sources,
            trace=self._trace(["Estimated fair probability for the target outcome."]),
        )


def final_decision(run_id: str, trace_id: str, estimate: ProbabilityOutput) -> FinalDecision:
    return FinalDecision(
        market_id=estimate.market_id,
        market_prob=estimate.market_prob,
        fair_prob=estimate.fair_prob,
        edge=estimate.edge,
        confidence=estimate.confidence,
        decision=estimate.decision,
        reasoning_summary=estimate.reasoning_summary,
        risks=estimate.risks,
        sources=estimate.sources,
        expected_value=estimate.expected_value,
        run_id=run_id,
        trace_id=trace_id,
        snapshot_as_of=None,
        agent_outputs=None,
    )
