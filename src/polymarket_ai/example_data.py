from __future__ import annotations

from datetime import datetime, timezone

from polymarket_ai.market_data.schemas import MarketRules, MarketStatus, NormalizedMarket, OutcomeQuote


def build_example_market() -> NormalizedMarket:
    return NormalizedMarket(
        event_id="weather_2026",
        market_id="atlantic_hurricanes_over_15_2026",
        question="Will there be more than 15 named Atlantic storms in 2026?",
        category="weather",
        end_date=datetime(2026, 12, 1, tzinfo=timezone.utc),
        status=MarketStatus.OPEN,
        liquidity=24000,
        volume_24h=8200,
        volume_total=120000,
        description="Seasonal weather market for Atlantic storm count.",
        rules=MarketRules(
            raw_rules=(
                "Resolves YES if the official NOAA or designated resolution source counts more than 15 "
                "named Atlantic storms during the 2026 Atlantic hurricane season."
            ),
            parsed_resolution_criteria=[
                "Use the designated official storm count source only.",
                "Threshold is strictly greater than 15 named storms.",
                "Final determination occurs after season-end official tally.",
            ],
            source_url="https://www.noaa.gov/",
        ),
        outcomes=[
            OutcomeQuote(
                outcome_id="yes",
                name="Yes",
                price=0.47,
                implied_probability=0.47,
            ),
            OutcomeQuote(
                outcome_id="no",
                name="No",
                price=0.53,
                implied_probability=0.53,
            ),
        ],
        best_bid=0.46,
        best_ask=0.48,
        last_price=0.47,
        attention_score=0.25,
    )
