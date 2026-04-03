from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from polymarket_ai.market_data.schemas import MarketRules, MarketSnapshot, MarketStatus, NormalizedMarket, OutcomeQuote
from polymarket_ai.reliability.retry import RetryPolicy, retry


_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


class MarketAdapter(Protocol):
    source_name: str

    def fetch_markets(self) -> MarketSnapshot:
        ...


class MarketLookupAdapter(MarketAdapter, Protocol):
    def fetch_market(self, market_id: str) -> NormalizedMarket:
        ...


class MarketEnrichmentAdapter(Protocol):
    source_name: str

    def enrich_market(self, market: NormalizedMarket) -> NormalizedMarket:
        ...


@dataclass(slots=True)
class StaticMarketAdapter:
    source_name: str
    markets: list[NormalizedMarket]

    def fetch_markets(self) -> MarketSnapshot:
        return MarketSnapshot(
            as_of=datetime.now(tz=timezone.utc),
            source=self.source_name,
            markets=self.markets,
        )


@dataclass(slots=True)
class GammaApiAdapter:
    base_url: str = "https://gamma-api.polymarket.com"
    timeout_seconds: float = 10.0
    default_limit: int = 100
    source_name: str = "gamma_api"

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def fetch_markets(self) -> MarketSnapshot:
        payload = self._request_json(
            "/markets",
            {
                "active": "true",
                "closed": "false",
                "limit": self.default_limit,
            },
        )
        if not isinstance(payload, list):
            raise ValueError("Gamma /markets response was not a list.")
        markets = [self._normalize_market(record) for record in payload]
        return MarketSnapshot(
            as_of=datetime.now(tz=timezone.utc),
            source=self.source_name,
            markets=markets,
        )

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def fetch_market(self, market_id: str) -> NormalizedMarket:
        payload = self._request_json(
            "/markets",
            {"id": market_id} if market_id.isdigit() else {"slug": market_id},
        )

        if isinstance(payload, list):
            if not payload:
                raise KeyError(f"Gamma market not found for {market_id}")
            exact = next(
                (
                    item
                    for item in payload
                    if item.get("slug") == market_id or str(item.get("id", "")) == market_id
                ),
                payload[0],
            )
            return self._normalize_market(exact)
        if isinstance(payload, dict):
            return self._normalize_market(payload)
        raise ValueError(f"Unexpected Gamma market payload type: {type(payload).__name__}")

    def _request_json(self, path: str, params: dict[str, Any] | None) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def _normalize_market(self, payload: dict[str, Any]) -> NormalizedMarket:
        raw_event = self._first_item(payload.get("events"))
        event_id = str((raw_event or {}).get("id") or payload.get("eventId") or payload.get("id"))
        category = (
            payload.get("category")
            or (raw_event or {}).get("category")
            or (raw_event or {}).get("seriesSlug")
            or (raw_event or {}).get("slug")
            or payload.get("groupItemTitle")
            or "unknown"
        )
        clob_token_ids = self._parse_json_list(payload.get("clobTokenIds"))
        outcomes = self._normalize_outcomes(
            names=self._parse_json_list(payload.get("outcomes")),
            prices=self._parse_json_list(payload.get("outcomePrices")),
            token_ids=clob_token_ids,
        )
        parsed_rules = self._parse_rules_text(str(payload.get("description") or ""))
        status = self._market_status(payload)
        return NormalizedMarket(
            event_id=event_id,
            market_id=str(payload.get("slug") or payload.get("id")),
            question=str(payload.get("question") or ""),
            category=str(category),
            slug=payload.get("slug"),
            condition_id=payload.get("conditionId"),
            event_slug=(raw_event or {}).get("slug") or payload.get("eventSlug"),
            end_date=self._parse_datetime(payload.get("endDate")),
            status=status,
            liquidity=self._coerce_float(payload.get("liquidityNum"), payload.get("liquidity")),
            volume_24h=self._coerce_float(payload.get("volume24hr"), payload.get("volume24hrClob")),
            volume_total=self._coerce_float(payload.get("volumeNum"), payload.get("volume")),
            description=payload.get("description"),
            rules=MarketRules(
                raw_rules=str(payload.get("description") or ""),
                parsed_resolution_criteria=parsed_rules,
                source_url=self._parse_source_url(payload.get("resolutionSource")),
            ),
            outcomes=outcomes,
            best_bid=self._coerce_optional_probability(payload.get("bestBid")),
            best_ask=self._coerce_optional_probability(payload.get("bestAsk")),
            last_price=self._coerce_optional_probability(payload.get("lastTradePrice")),
            spread=self._coerce_optional_probability(payload.get("spread")),
            clob_token_ids=clob_token_ids,
            attention_score=self._attention_score(
                volume_24h=self._coerce_float(payload.get("volume24hr"), payload.get("volume24hrClob")),
                comment_count=int((raw_event or {}).get("commentCount") or payload.get("commentCount") or 0),
                competitive=self._coerce_float(payload.get("competitive")),
            ),
        )

    def _normalize_outcomes(
        self,
        names: list[str],
        prices: list[str],
        token_ids: list[str],
    ) -> list[OutcomeQuote]:
        if not names:
            names = ["Yes", "No"]
        parsed_prices = [self._coerce_probability(price) for price in prices]
        while len(parsed_prices) < len(names):
            parsed_prices.append(0.0)
        return [
            OutcomeQuote(
                outcome_id=self._slugify(name) or f"outcome_{index}",
                name=name,
                price=parsed_prices[index],
                implied_probability=parsed_prices[index],
                token_id=token_ids[index] if index < len(token_ids) else None,
            )
            for index, name in enumerate(names)
        ]

    def _parse_rules_text(self, raw_rules: str) -> list[str]:
        return [
            block.strip().replace("\n", " ")
            for block in raw_rules.split("\n\n")
            if block.strip()
        ]

    def _parse_json_list(self, raw_value: Any) -> list[str]:
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            return [str(item) for item in raw_value]
        if isinstance(raw_value, str):
            stripped = raw_value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            return [str(parsed)]
        return [str(raw_value)]

    def _market_status(self, payload: dict[str, Any]) -> MarketStatus:
        if payload.get("closed") is True:
            return MarketStatus.CLOSED
        if payload.get("active") is True:
            return MarketStatus.OPEN
        return MarketStatus.RESOLVED if payload.get("archived") else MarketStatus.CLOSED

    def _coerce_float(self, primary: Any, fallback: Any = 0.0) -> float:
        for value in (primary, fallback):
            if value is None or value == "":
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _coerce_probability(self, value: Any) -> float:
        return min(1.0, max(0.0, self._coerce_float(value, 0.0)))

    def _coerce_optional_probability(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        return self._coerce_probability(value)

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _parse_source_url(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        candidate = value.strip()
        if not candidate.startswith(("http://", "https://")):
            return None
        return candidate

    def _first_item(self, value: Any) -> dict[str, Any] | None:
        if isinstance(value, list) and value:
            first = value[0]
            return first if isinstance(first, dict) else None
        return None

    def _slugify(self, value: str) -> str:
        return _SLUG_CHARS.sub("_", value.strip().lower()).strip("_")

    def _attention_score(self, volume_24h: float, comment_count: int, competitive: float) -> float:
        volume_component = min(0.45, volume_24h / 50_000)
        comment_component = min(0.35, comment_count / 5_000)
        competitive_component = min(0.20, max(0.0, competitive) * 0.20)
        return min(1.0, volume_component + comment_component + competitive_component)


@dataclass(slots=True)
class DataApiAdapter:
    base_url: str = "https://data-api.polymarket.com"
    timeout_seconds: float = 10.0
    default_limit: int = 100
    source_name: str = "data_api"

    def fetch_markets(self) -> MarketSnapshot:
        return MarketSnapshot(
            as_of=datetime.now(tz=timezone.utc),
            source=self.source_name,
            markets=[],
        )

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def enrich_market(self, market: NormalizedMarket) -> NormalizedMarket:
        if not market.condition_id:
            return market
        trades = self._fetch_trades(market.condition_id)
        if not trades:
            return market
        buy_volume = sum(
            self._coerce_float(trade.get("size"))
            for trade in trades
            if str(trade.get("side", "")).upper() == "BUY"
        )
        sell_volume = sum(
            self._coerce_float(trade.get("size"))
            for trade in trades
            if str(trade.get("side", "")).upper() == "SELL"
        )
        last_timestamp = max(int(trade.get("timestamp", 0) or 0) for trade in trades)
        recent_trade_volume = buy_volume + sell_volume
        activity_attention = min(1.0, 0.15 + len(trades) / 150 + recent_trade_volume / 50_000)
        return market.model_copy(
            update={
                "recent_trade_count": len(trades),
                "recent_trade_volume": recent_trade_volume,
                "recent_buy_volume": buy_volume,
                "recent_sell_volume": sell_volume,
                "last_activity_at": datetime.fromtimestamp(last_timestamp, tz=timezone.utc),
                "attention_score": max(market.attention_score, activity_attention),
            }
        )

    def _fetch_trades(self, condition_id: str) -> list[dict[str, Any]]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(
                "/trades",
                params={"market": condition_id, "limit": self.default_limit},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Data API /trades response was not a list.")
        return [
            trade
            for trade in payload
            if isinstance(trade, dict) and trade.get("conditionId") == condition_id
        ]

    def _coerce_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class ClobOrderbookAdapter:
    source_name = "clob"

    def fetch_markets(self) -> MarketSnapshot:
        raise NotImplementedError("Wire official CLOB fetch here.")
