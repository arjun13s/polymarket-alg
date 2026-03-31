from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

T = TypeVar("T")


def run_with_timeout(func: Callable[[], T], timeout_seconds: int) -> T:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds") from exc
