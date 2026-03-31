from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"


@dataclass(slots=True)
class CircuitBreakerState:
    failures: int = 0
    opened_until: datetime | None = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: int = 60) -> None:
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_timeout_seconds
        self._state = CircuitBreakerState()

    def allow(self) -> bool:
        if self._state.opened_until is None:
            return True
        return datetime.now(tz=timezone.utc) >= self._state.opened_until

    @property
    def state(self) -> CircuitState:
        return CircuitState.OPEN if self._state.opened_until is not None else CircuitState.CLOSED

    def record_success(self) -> None:
        self._state = CircuitBreakerState()

    def record_failure(self) -> None:
        self._state.failures += 1
        if self._state.failures >= self._failure_threshold:
            self._state.opened_until = datetime.now(tz=timezone.utc) + timedelta(
                seconds=self._reset_seconds
            )
