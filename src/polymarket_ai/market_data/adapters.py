from __future__ import annotations

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
class KalshiMarketsAdapter:
    base_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    timeout_seconds: float = 10.0
    default_limit: int = 100
    source_name: str = "kalshi_markets_api"

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def fetch_markets(self) -> MarketSnapshot:
        payload = self._request_json(
            "/markets",
            {
                "status": "open",
                "limit": self.default_limit,
            },
        )
        raw_markets = self._require_list(payload.get("markets") if isinstance(payload, dict) else None)
        markets = [self._normalize_market(record) for record in raw_markets]
        return MarketSnapshot(
            as_of=datetime.now(tz=timezone.utc),
            source=self.source_name,
            markets=markets,
        )

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def fetch_market(self, market_id: str) -> NormalizedMarket:
        payload = self._request_json(f"/markets/{market_id}", params=None)
        if not isinstance(payload, dict) or not isinstance(payload.get("market"), dict):
            raise KeyError(f"Kalshi market not found for {market_id}")
        return self._normalize_market(payload["market"])

    def _request_json(self, path: str, params: dict[str, Any] | None) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def _normalize_market(self, payload: dict[str, Any]) -> NormalizedMarket:
        ticker = str(payload.get("ticker") or "").strip()
        if not ticker:
            raise ValueError("Kalshi market payload is missing ticker.")

        event_ticker = str(payload.get("event_ticker") or ticker).strip()
        status = self._market_status(payload.get("status"))
        yes_bid = self._coerce_optional_probability(payload.get("yes_bid_dollars"), payload.get("yes_bid"))
        yes_ask = self._coerce_optional_probability(payload.get("yes_ask_dollars"), payload.get("yes_ask"))
        no_bid = self._coerce_optional_probability(payload.get("no_bid_dollars"), payload.get("no_bid"))
        no_ask = self._coerce_optional_probability(payload.get("no_ask_dollars"), payload.get("no_ask"))
        last_price = self._coerce_optional_probability(payload.get("last_price_dollars"), payload.get("last_price"))
        yes_price = self._select_price(last_price, yes_ask, yes_bid)
        no_price = self._select_price(None if last_price is None else 1.0 - last_price, no_ask, no_bid)
        raw_rules = self._join_rules(payload.get("rules_primary"), payload.get("rules_secondary"))
        volume_total = self._coerce_float(payload.get("volume_fp"), payload.get("volume"), payload.get("volume_dollars"))
        volume_24h = self._coerce_float(
            payload.get("volume_24h_fp"),
            payload.get("volume_24h"),
            payload.get("volume_24h_dollars"),
        )
        liquidity = self._coerce_float(
            payload.get("liquidity_dollars"),
            payload.get("liquidity"),
            payload.get("liquidity_value"),
        )
        open_interest = self._coerce_float(
            payload.get("open_interest_fp"),
            payload.get("open_interest"),
            payload.get("open_interest_dollars"),
        )

        return NormalizedMarket(
            venue="kalshi",
            event_id=event_ticker,
            market_id=ticker,
            question=str(payload.get("title") or payload.get("subtitle") or ticker),
            category=str(payload.get("category") or payload.get("series_ticker") or "kalshi"),
            series_id=self._optional_str(payload.get("series_ticker")),
            slug=self._slugify(ticker),
            event_slug=self._slugify(event_ticker),
            end_date=self._parse_datetime(payload.get("close_time") or payload.get("expiration_time")),
            status=status,
            liquidity=liquidity,
            volume_24h=volume_24h,
            volume_total=volume_total,
            description=payload.get("subtitle") or payload.get("title"),
            rules=MarketRules(
                raw_rules=raw_rules,
                parsed_resolution_criteria=self._parse_rules_text(raw_rules),
                source_url=self._parse_source_url(payload.get("settlement_source")),
                source_name=self._parse_source_name(payload.get("settlement_source")),
            ),
            outcomes=[
                OutcomeQuote(
                    outcome_id="yes",
                    name=str(payload.get("yes_sub_title") or "Yes"),
                    price=yes_price,
                    implied_probability=yes_price,
                ),
                OutcomeQuote(
                    outcome_id="no",
                    name=str(payload.get("no_sub_title") or "No"),
                    price=no_price,
                    implied_probability=no_price,
                ),
            ],
            best_bid=yes_bid,
            best_ask=yes_ask,
            last_price=last_price,
            spread=self._spread(yes_bid, yes_ask),
            attention_score=self._attention_score(volume_24h=volume_24h, liquidity=liquidity, open_interest=open_interest),
        )

    def _require_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise ValueError("Kalshi /markets response did not contain a markets list.")
        return [item for item in value if isinstance(item, dict)]

    def _market_status(self, value: Any) -> MarketStatus:
        normalized = str(value or "").strip().lower()
        if normalized in {"active", "open", "paused"}:
            return MarketStatus.OPEN
        if normalized in {"settled", "finalized", "resolved", "determined"}:
            return MarketStatus.RESOLVED
        return MarketStatus.CLOSED

    def _parse_rules_text(self, raw_rules: str) -> list[str]:
        return [block.strip().replace("\n", " ") for block in raw_rules.split("\n\n") if block.strip()]

    def _join_rules(self, primary: Any, secondary: Any) -> str:
        parts = [str(item).strip() for item in (primary, secondary) if str(item or "").strip()]
        return "\n\n".join(parts)

    def _coerce_float(self, *values: Any) -> float:
        for value in values:
            if value is None or value == "":
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _coerce_optional_probability(self, *values: Any) -> float | None:
        for value in values:
            if value is None or value == "":
                continue
            return min(1.0, max(0.0, self._coerce_float(value)))
        return None

    def _select_price(self, last_price: float | None, best_ask: float | None, best_bid: float | None) -> float:
        if last_price is not None:
            return round(last_price, 6)
        if best_ask is not None and best_bid is not None:
            return round(min(1.0, max(0.0, (best_ask + best_bid) / 2)), 6)
        if best_ask is not None:
            return round(best_ask, 6)
        if best_bid is not None:
            return round(best_bid, 6)
        return 0.5

    def _spread(self, best_bid: float | None, best_ask: float | None) -> float | None:
        if best_bid is None or best_ask is None:
            return None
        return round(max(0.0, best_ask - best_bid), 6)

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

    def _parse_source_name(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        candidate = value.strip()
        if not candidate or candidate.startswith(("http://", "https://")):
            return None
        return candidate

    def _optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        candidate = str(value).strip()
        return candidate or None

    def _slugify(self, value: str) -> str:
        return _SLUG_CHARS.sub("_", value.strip().lower()).strip("_")

    def _attention_score(self, volume_24h: float, liquidity: float, open_interest: float) -> float:
        volume_component = min(0.45, volume_24h / 250_000)
        liquidity_component = min(0.30, liquidity / 500_000)
        oi_component = min(0.25, open_interest / 250_000)
        return min(1.0, volume_component + liquidity_component + oi_component)


@dataclass(slots=True)
class KalshiTradesAdapter:
    base_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    timeout_seconds: float = 10.0
    default_limit: int = 100
    source_name: str = "kalshi_trades_api"

    def fetch_markets(self) -> MarketSnapshot:
        return MarketSnapshot(
            as_of=datetime.now(tz=timezone.utc),
            source=self.source_name,
            markets=[],
        )

    @retry(RetryPolicy(max_attempts=2, backoff_seconds=0.2))
    def enrich_market(self, market: NormalizedMarket) -> NormalizedMarket:
        trades = self._fetch_trades(market.market_id)
        if not trades:
            return market

        yes_volume = sum(
            self._coerce_float(trade.get("count_fp"), trade.get("count"))
            for trade in trades
            if str(trade.get("taker_side", "")).lower() == "yes"
        )
        no_volume = sum(
            self._coerce_float(trade.get("count_fp"), trade.get("count"))
            for trade in trades
            if str(trade.get("taker_side", "")).lower() == "no"
        )
        trade_times = [self._parse_datetime(trade.get("created_time")) for trade in trades]
        last_activity_at = max((value for value in trade_times if value is not None), default=None)
        recent_trade_volume = yes_volume + no_volume
        activity_attention = min(1.0, 0.15 + len(trades) / 150 + recent_trade_volume / 100_000)
        return market.model_copy(
            update={
                "recent_trade_count": len(trades),
                "recent_trade_volume": recent_trade_volume,
                "recent_buy_volume": yes_volume,
                "recent_sell_volume": no_volume,
                "last_activity_at": last_activity_at,
                "attention_score": max(market.attention_score, activity_attention),
            }
        )

    def _fetch_trades(self, ticker: str) -> list[dict[str, Any]]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(
                "/markets/trades",
                params={"ticker": ticker, "limit": self.default_limit},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("trades"), list):
            raise ValueError("Kalshi /markets/trades response did not contain a trades list.")
        return [
            trade
            for trade in payload["trades"]
            if isinstance(trade, dict) and str(trade.get("ticker") or "") == ticker
        ]

    def _coerce_float(self, *values: Any) -> float:
        for value in values:
            if value is None or value == "":
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None


class KalshiOrderbookAdapter:
    source_name = "kalshi_orderbook"

    def fetch_markets(self) -> MarketSnapshot:
        raise NotImplementedError("Wire Kalshi orderbook reads here if you need deeper spread/depth features.")


# Backward-compatible aliases while the package namespace still uses polymarket_ai.
GammaApiAdapter = KalshiMarketsAdapter
DataApiAdapter = KalshiTradesAdapter
ClobOrderbookAdapter = KalshiOrderbookAdapter
