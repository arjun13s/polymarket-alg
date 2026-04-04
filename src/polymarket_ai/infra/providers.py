from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from polymarket_ai.research.schemas import ResearchPacket


@dataclass(slots=True)
class ModelRequest:
    task_name: str
    prompt: str
    model: str


class ModelProvider(Protocol):
    def estimate_probability(
        self,
        packet: ResearchPacket,
        outcome_id: str,
    ) -> "ProbabilityAssessment":
        ...


@dataclass(slots=True)
class ProbabilityAssessment:
    fair_probability: float
    lower_bound: float
    upper_bound: float
    rationale: str


class ProbabilityAssessmentPayload(BaseModel):
    fair_probability: float = Field(ge=0.0, le=1.0)
    lower_bound: float = Field(ge=0.0, le=1.0)
    upper_bound: float = Field(ge=0.0, le=1.0)
    rationale: str


class ProviderResponseError(RuntimeError):
    pass


class HeuristicModelProvider:
    """Fallback provider for local development and deterministic tests."""

    def estimate_probability(
        self,
        packet: ResearchPacket,
        outcome_id: str,
    ) -> ProbabilityAssessment:
        support = sum(claim.weight for claim in packet.supporting_claims)
        oppose = sum(claim.weight for claim in packet.opposing_claims)
        total = max(support + oppose, 1.0)
        fair_probability = max(min(support / total, 0.99), 0.01)
        uncertainty = min(0.45, 0.10 + (1.0 - packet.source_quality_score) * 0.35)
        rationale = (
            "Heuristic provider used. Replace with an OpenAI-compatible or HUD-compatible "
            "provider in polymarket_ai.infra.providers."
        )
        return ProbabilityAssessment(
            fair_probability=fair_probability,
            lower_bound=max(fair_probability - uncertainty / 2, 0.0),
            upper_bound=min(fair_probability + uncertainty / 2, 1.0),
            rationale=rationale,
        )


@dataclass(slots=True)
class HudOpenAICompatibleProvider:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 30.0

    @staticmethod
    def _extract_json_payload(content: str) -> dict[str, object]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("HUD provider returned non-JSON content.") from exc
        if not isinstance(parsed, dict):
            raise ProviderResponseError("HUD provider returned a non-object JSON payload.")
        return parsed

    def estimate_probability(
        self,
        packet: ResearchPacket,
        outcome_id: str,
    ) -> ProbabilityAssessment:
        prompt = (
            "Return strict JSON with keys fair_probability, lower_bound, upper_bound, rationale. "
            "You are estimating the probability for the target Kalshi outcome using the provided "
            "research packet. Penalize low-quality sources, stale evidence, ambiguous rules, and "
            "markets that may already be efficiently priced.\n\n"
            f"Target outcome: {outcome_id}\n"
            f"Question: {packet.question}\n"
            f"Rules: {packet.rules_summary}\n"
            f"Supporting claims: {[claim.model_dump(mode='json') for claim in packet.supporting_claims]}\n"
            f"Opposing claims: {[claim.model_dump(mode='json') for claim in packet.opposing_claims]}\n"
            f"Why crowd might be wrong: {packet.crowd_might_be_wrong}\n"
            f"Why we might be wrong: {packet.we_might_be_wrong}\n"
            f"Rule risk notes: {packet.rule_risk_notes}\n"
            f"Source quality score: {packet.source_quality_score}\n"
            f"Evidence freshness score: {packet.evidence_freshness_score}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a trading research model. Output only valid JSON. "
                        "Probabilities must be between 0 and 1."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        parsed = self._extract_json_payload(content)
        try:
            validated = ProbabilityAssessmentPayload.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderResponseError("HUD provider returned an invalid probability payload.") from exc
        if validated.lower_bound > validated.upper_bound:
            raise ProviderResponseError("HUD provider returned an inverted probability interval.")
        return ProbabilityAssessment(
            fair_probability=validated.fair_probability,
            lower_bound=validated.lower_bound,
            upper_bound=validated.upper_bound,
            rationale=validated.rationale,
        )


def create_default_provider(settings: "Settings", file_provider: str | None = None) -> ModelProvider:
    provider_name = (settings.provider or file_provider or "hud").lower()
    if provider_name == "hud" and settings.hud_base_url and settings.hud_api_key:
        return HudOpenAICompatibleProvider(
            base_url=settings.hud_base_url,
            api_key=settings.hud_api_key,
            model=settings.hud_model or "hud-reasoner",
        )
    return HeuristicModelProvider()
