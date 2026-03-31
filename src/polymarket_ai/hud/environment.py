from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Protocol

from polymarket_ai.hud.models import ScenarioResult


@dataclass(slots=True)
class EnvTool:
    name: str
    description: str
    handler: Callable[..., Any]


@dataclass(slots=True)
class ScenarioSpec:
    name: str
    description: str
    handler: Callable[..., ScenarioResult]


class ToolCallable(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class PredictionMarketEnv:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, EnvTool] = {}
        self.scenarios: dict[str, ScenarioSpec] = {}

    def tool(self, name: str | None = None, description: str = "") -> Callable[[ToolCallable], ToolCallable]:
        def decorator(fn: ToolCallable) -> ToolCallable:
            tool_name = name or fn.__name__
            self.tools[tool_name] = EnvTool(name=tool_name, description=description, handler=fn)

            @wraps(fn)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)

            return wrapped  # type: ignore[return-value]

        return decorator

    def scenario(self, name: str | None = None, description: str = "") -> Callable[[Callable[..., ScenarioResult]], Callable[..., ScenarioResult]]:
        def decorator(fn: Callable[..., ScenarioResult]) -> Callable[..., ScenarioResult]:
            scenario_name = name or fn.__name__
            self.scenarios[scenario_name] = ScenarioSpec(name=scenario_name, description=description, handler=fn)
            return fn

        return decorator

    def call_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self.tools[name].handler(*args, **kwargs)

    def run_scenario(self, name: str, *args: Any, **kwargs: Any) -> ScenarioResult:
        return self.scenarios[name].handler(*args, **kwargs)


prediction_market_env = PredictionMarketEnv(name="prediction_market_env")
