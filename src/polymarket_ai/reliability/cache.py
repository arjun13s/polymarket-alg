from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class CacheEntry(Generic[T]):
    value: T
    expires_at: datetime


class TTLCacheStore(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(tz=timezone.utc):
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = CacheEntry(
            value=value,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(seconds=self._ttl_seconds),
        )

    def get_or_set(self, key: str, loader: Callable[[], T]) -> T:
        value = self.get(key)
        if value is not None:
            return value
        loaded = loader()
        self.set(key, loaded)
        return loaded


class TimedCache(TTLCacheStore[T]):
    def set(self, key: str, value: T, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is None:
            return super().set(key, value)
        self._store[key] = CacheEntry(
            value=value,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(seconds=ttl_seconds),
        )
