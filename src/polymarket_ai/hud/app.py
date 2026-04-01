from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polymarket_ai.hud.environment import create_environment
from polymarket_ai.hud.orchestrator import PredictionMarketOrchestrator
from polymarket_ai.hud.runtime import HUDRuntime, build_hud_runtime
from polymarket_ai.hud.scenarios import register_scenarios
from polymarket_ai.hud.tools import register_tools
from polymarket_ai.infra.config import Settings


@dataclass(slots=True)
class HUDApplication:
    settings: Settings
    runtime: HUDRuntime
    orchestrator: PredictionMarketOrchestrator
    env: Any


def create_hud_app(settings: Settings | None = None) -> HUDApplication:
    resolved_settings = settings or Settings()
    runtime = build_hud_runtime(resolved_settings)
    orchestrator = PredictionMarketOrchestrator(runtime=runtime, settings=resolved_settings)
    env = create_environment(resolved_settings.hud_environment_name)
    register_tools(env, runtime=runtime, orchestrator=orchestrator)
    register_scenarios(env, runtime=runtime, orchestrator=orchestrator, settings=resolved_settings)
    return HUDApplication(
        settings=resolved_settings,
        runtime=runtime,
        orchestrator=orchestrator,
        env=env,
    )
