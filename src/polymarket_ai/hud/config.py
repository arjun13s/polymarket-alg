from __future__ import annotations

from dataclasses import dataclass

from polymarket_ai.infra.config import AgentRoute, Settings

HUDSettings = Settings


@dataclass(slots=True)
class ModelRoute:
    tier: str
    model: str
    purpose: str
    max_retries: int
    timeout_seconds: int
    allowed_tools: tuple[str, ...] = ()


def build_model_routes(settings: Settings) -> dict[str, ModelRoute]:
    tiers = {
        "orchestrator": "high",
        "rules": "cheap",
        "research": "mid",
        "skeptic": "mid",
        "probability": "high",
    }
    purposes = {
        "orchestrator": "top-level orchestration",
        "rules": "rule parsing",
        "research": "evidence gathering",
        "skeptic": "counter-argument generation",
        "probability": "probability synthesis",
    }
    routes: dict[str, ModelRoute] = {}
    for role, route in settings.model_routes().items():
        routes[role] = _to_model_route(route, tier=tiers[role], purpose=purposes[role])
    return routes


def _to_model_route(route: AgentRoute, tier: str, purpose: str) -> ModelRoute:
    return ModelRoute(
        tier=tier,
        model=route.model,
        purpose=purpose,
        max_retries=route.max_retries,
        timeout_seconds=route.timeout_seconds,
        allowed_tools=tuple(route.allowed_tools),
    )
