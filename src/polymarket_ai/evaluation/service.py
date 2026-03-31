from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationRecord:
    market_id: str
    fair_probability: float
    market_probability: float
    realized_outcome: int
    category: str


@dataclass(slots=True)
class EvaluationSummary:
    brier_score: float
    hit_rate: float
    average_edge: float
    total_records: int


class EvaluationService:
    def summarize(self, records: list[EvaluationRecord]) -> EvaluationSummary:
        if not records:
            return EvaluationSummary(0.0, 0.0, 0.0, 0)
        brier = sum((record.fair_probability - record.realized_outcome) ** 2 for record in records) / len(
            records
        )
        hit_rate = sum(
            1
            for record in records
            if (record.fair_probability >= 0.5 and record.realized_outcome == 1)
            or (record.fair_probability < 0.5 and record.realized_outcome == 0)
        ) / len(records)
        avg_edge = sum(record.fair_probability - record.market_probability for record in records) / len(
            records
        )
        return EvaluationSummary(
            brier_score=brier,
            hit_rate=hit_rate,
            average_edge=avg_edge,
            total_records=len(records),
        )
