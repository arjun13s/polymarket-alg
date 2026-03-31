from __future__ import annotations

from dataclasses import dataclass
from pydantic_settings import BaseSettings, SettingsConfigDict


class HUDSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POLYMARKET_AI_", env_file=".env", extra="ignore")

    provider: str = "hud"
    hud_base_url: str | None = None
    hud_api_key: str | None = None
    high_capability_model: str = "hud-pro"
    mid_tier_model: str = "hud-balanced"
    cheap_model: str = "hud-lite"
    min_edge: float = 0.05
    min_confidence: float = 0.65
    watchlist_confidence: float = 0.45
    fee_bps: int = 150
    slippage_bps: int = 50
    market_cache_ttl_seconds: int = 300


@dataclass(slots=True)
class ModelRoute:
    tier: str
    model: str
    purpose: str
