from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from polymarket_ai.storage.models import Base


class MarketRecord(Base):
    __tablename__ = "hud_markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text)


class ResearchRecord(Base):
    __tablename__ = "hud_research"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)


class RunRecord(Base):
    __tablename__ = "hud_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(String(64))
    finished_at: Mapped[str] = mapped_column(String(64))


class TradeRecord(Base):
    __tablename__ = "hud_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    expected_value: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(Text)
