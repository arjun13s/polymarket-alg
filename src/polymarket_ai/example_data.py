from __future__ import annotations

from datetime import datetime, timezone

from polymarket_ai.market_data.schemas import MarketRules, MarketStatus, NormalizedMarket, OutcomeQuote


def build_example_market() -> NormalizedMarket:
    return NormalizedMarket(
        event_id="KXATLANTICSTORMS-26",
        market_id="KXATLANTICSTORMS-26-N16",
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
                "Resolves YES if NOAA's final seasonal tally shows more than 15 named Atlantic storms "
                "during the 2026 Atlantic hurricane season. Determined by NOAA advisories and the "
                "post-season report."
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
        recent_trade_count=24,
        recent_trade_volume=512.0,
        recent_buy_volume=290.0,
        recent_sell_volume=222.0,
        last_activity_at=datetime(2026, 4, 1, 18, 30, tzinfo=timezone.utc),
        attention_score=0.25,
    )
