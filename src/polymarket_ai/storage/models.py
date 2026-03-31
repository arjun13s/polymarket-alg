from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MarketSnapshotRecord(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[str] = mapped_column(Text)


class ResearchRunRecord(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    outcome_id: Mapped[str] = mapped_column(String(128), index=True)
    recommendation: Mapped[str] = mapped_column(String(32), index=True)
    fair_probability: Mapped[float] = mapped_column(Float)
    edge: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(Text)


class WorkflowRunRecord(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    outcome_id: Mapped[str] = mapped_column(String(128), index=True)
    snapshot_record_id: Mapped[int] = mapped_column(Integer)
    snapshot_as_of: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[str] = mapped_column(String(64))
    finished_at: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)


class PaperTradeRecord(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    outcome_id: Mapped[str] = mapped_column(String(128), index=True)
    side: Mapped[str] = mapped_column(String(32))
    stake: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(Text)


class ExecutionDecisionRecord(Base):
    __tablename__ = "execution_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(128), index=True)
    outcome_id: Mapped[str] = mapped_column(String(128), index=True)
    blocked: Mapped[str] = mapped_column(String(8))
    recommended_stake: Mapped[float] = mapped_column(Float)
    execution_status: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[str] = mapped_column(Text)
