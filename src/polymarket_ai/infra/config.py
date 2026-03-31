from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from polymarket_ai.infra.paths import resolve_project_path


class SystemConfig(BaseModel):
    paper_mode: bool = True
    polling_interval_seconds: int = 300
    provider: str | None = None


class MarketDataConfig(BaseModel):
    min_liquidity: float = 1000.0
    min_volume: float = 1000.0


class PricingConfig(BaseModel):
    min_edge: float = 0.03
    max_uncertainty_width: float = 0.20
    min_confidence: float = 0.60
    watchlist_confidence: float = 0.45
    paper_trade_confidence: float = 0.70


class RankingConfig(BaseModel):
    freshness_half_life_hours: int = 24
    minimum_rank_score: float = 0.20


class PortfolioConfig(BaseModel):
    bankroll: float = 10000.0
    max_exposure_per_market: float = 0.02
    max_exposure_per_theme: float = 0.10


class FileConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    market_data: MarketDataConfig = Field(default_factory=MarketDataConfig)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLYMARKET_AI_",
        env_file=".env",
        extra="ignore",
    )

    env: str = "dev"
    db_url: str = "sqlite:///data/polymarket_ai.db"
    log_level: str = "INFO"
    default_fee_bps: int = 150
    default_slippage_bps: int = 50
    provider: str = "hud"
    orchestrator_model: str = "hud-orchestrator"
    research_model: str = "hud-research"
    rules_model: str = "hud-rules"
    skeptic_model: str = "hud-skeptic"
    probability_model: str = "hud-reasoner"
    cheap_model: str = "hud-cheap"
    tool_timeout_seconds: int = 30
    tool_max_retries: int = 2
    cache_ttl_seconds: int = 3600
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4"
    hud_base_url: str | None = None
    hud_api_key: str | None = None
    hud_model: str | None = None
    config_path: str = "configs/base.yaml"

    def load_file_config(self) -> FileConfig:
        path = resolve_project_path(self.config_path)
        if not path.exists():
            return FileConfig()
        with path.open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = yaml.safe_load(handle) or {}
        return FileConfig.model_validate(raw)

    def resolved_db_url(self) -> str:
        if self.db_url.startswith("sqlite:///"):
            raw_path = self.db_url.replace("sqlite:///", "", 1)
            return f"sqlite:///{resolve_project_path(raw_path)}"
        return self.db_url
