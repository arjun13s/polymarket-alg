from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.1
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,)


def retry_call(
    func: Callable[[], T],
    *,
    retries: int,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    delay_seconds: float = 0.1,
) -> T:
    last_error: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return func()
        except retry_exceptions as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def retry(policy: RetryPolicy) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapped(*args: object, **kwargs: object) -> T:
            def invoke() -> T:
                return func(*args, **kwargs)

            return retry_call(
                invoke,
                retries=max(policy.max_attempts - 1, 0),
                retry_exceptions=policy.retry_exceptions,
                delay_seconds=policy.backoff_seconds,
            )

        return wrapped

    return decorator
