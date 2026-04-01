from __future__ import annotations

import inspect
from dataclasses import dataclass, field
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


@dataclass(slots=True)
class PredictionMarketEnv:
    name: str
    tools: dict[str, EnvTool] = field(default_factory=dict)
    scenarios: dict[str, ScenarioSpec] = field(default_factory=dict)
    startup_hooks: list[Callable[..., Any]] = field(default_factory=list)
    shutdown_hooks: list[Callable[..., Any]] = field(default_factory=list)

    def tool(self, name: str | None = None, description: str = "") -> Callable[[ToolCallable], ToolCallable]:
        def decorator(fn: ToolCallable) -> ToolCallable:
            tool_name = name or fn.__name__
            self.tools[tool_name] = EnvTool(name=tool_name, description=description, handler=fn)

            @wraps(fn)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)

            return wrapped  # type: ignore[return-value]

        return decorator

    def scenario(
        self,
        name: str | None = None,
        description: str = "",
    ) -> Callable[[Callable[..., ScenarioResult]], Callable[..., ScenarioResult]]:
        def decorator(fn: Callable[..., ScenarioResult]) -> Callable[..., ScenarioResult]:
            scenario_name = name or fn.__name__
            self.scenarios[scenario_name] = ScenarioSpec(
                name=scenario_name,
                description=description,
                handler=fn,
            )
            return fn

        return decorator

    def initialize(self, fn: Callable[..., Any] | None = None) -> Callable[..., Any]:
        def decorator(hook: Callable[..., Any]) -> Callable[..., Any]:
            self.startup_hooks.append(hook)
            return hook

        return decorator(fn) if fn is not None else decorator

    def shutdown(self, fn: Callable[..., Any] | None = None) -> Callable[..., Any]:
        def decorator(hook: Callable[..., Any]) -> Callable[..., Any]:
            self.shutdown_hooks.append(hook)
            return hook

        return decorator(fn) if fn is not None else decorator

    def call_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self.tools[name].handler(*args, **kwargs)

    def run_scenario(self, name: str, *args: Any, **kwargs: Any) -> ScenarioResult:
        return self.scenarios[name].handler(*args, **kwargs)

    def run(self) -> None:
        raise RuntimeError(
            "Local fallback environment does not expose an MCP server. "
            "Use the root-level controller package inside HUD, or install the newer HUD SDK."
        )


def create_environment(name: str) -> Any:
    try:
        from hud import Environment as HudEnvironment  # type: ignore

        if callable(getattr(HudEnvironment, "tool", None)) and callable(
            getattr(HudEnvironment, "scenario", None)
        ):
            try:
                return HudEnvironment(name=name)
            except TypeError:
                pass
    except Exception:
        pass
    return PredictionMarketEnv(name=name)


def call_hook(hook: Callable[..., Any]) -> None:
    result = hook()
    if inspect.isawaitable(result):
        raise RuntimeError("Async HUD hooks are not supported in the local fallback environment.")
