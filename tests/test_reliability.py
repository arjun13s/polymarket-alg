from __future__ import annotations

from polymarket_ai.reliability.cache import TimedCache
from polymarket_ai.reliability.circuit_breaker import CircuitBreaker, CircuitState
from polymarket_ai.reliability.retry import RetryPolicy, retry


def test_circuit_breaker_opens_and_recovers() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0)
    assert breaker.allow() is True
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow() is True


def test_timed_cache_get_or_set() -> None:
    cache = TimedCache[str](ttl_seconds=60)
    calls = {"count": 0}

    def loader() -> str:
        calls["count"] += 1
        return "value"

    assert cache.get_or_set("key", loader) == "value"
    assert cache.get_or_set("key", loader) == "value"
    assert calls["count"] == 1


def test_retry_decorator_retries() -> None:
    attempts = {"count": 0}

    @retry(RetryPolicy(max_attempts=3, backoff_seconds=0.0, retry_exceptions=(RuntimeError,)))
    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 3
