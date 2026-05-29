"""
Pure data models and parsers for Polymarket API payloads.

This module imports nothing from Home Assistant or aiohttp so it can be
unit-tested in isolation. All parsers are defensive: the Gamma API returns
some list fields as JSON-encoded strings and some numerics as strings, and
keys may be absent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


def _as_float(value: Any) -> float:
    """Coerce a possibly-string, possibly-missing value to float (0.0 fallback)."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_optional_float(value: Any) -> float | None:
    """Coerce to float, returning None when missing or unparseable."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str_list(value: Any) -> list[str]:
    """Parse a field that may be a list or a JSON-encoded list-of-strings."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def _as_float_list(value: Any) -> list[float]:
    """Parse a field that may be a list or a JSON-encoded list of numbers."""
    return [_as_float(item) for item in _as_str_list(value)]


@dataclass
class MarketInfo:
    """Normalized view of one Polymarket binary market."""

    market_id: str
    question: str
    slug: str
    event_title: str
    event_slug: str
    outcomes: list[str]
    prices: list[float]
    clob_token_ids: list[str]
    yes_price: float | None
    yes_token_id: str | None
    best_bid: float | None
    best_ask: float | None
    last_trade_price: float | None
    one_day_price_change: float | None
    volume: float
    volume_24hr: float
    liquidity: float
    end_date: str | None
    active: bool
    closed: bool
    icon: str | None
    # Live midpoint from the CLOB API; filled in by the coordinator (optional).
    midpoint: float | None = field(default=None)


def parse_market(
    raw: dict[str, Any], *, event_title: str, event_slug: str
) -> MarketInfo:
    """Build a MarketInfo from a Gamma `markets[]` entry."""
    outcomes = _as_str_list(raw.get("outcomes"))
    prices = _as_float_list(raw.get("outcomePrices"))
    token_ids = _as_str_list(raw.get("clobTokenIds"))

    yes_price: float | None = None
    yes_token_id: str | None = None
    if "Yes" in outcomes:
        idx = outcomes.index("Yes")
        if idx < len(prices):
            yes_price = prices[idx]
        if idx < len(token_ids):
            yes_token_id = token_ids[idx]

    return MarketInfo(
        market_id=str(raw.get("id", "")),
        question=str(raw.get("question", "")),
        slug=str(raw.get("slug", "")),
        event_title=event_title,
        event_slug=event_slug,
        outcomes=outcomes,
        prices=prices,
        clob_token_ids=token_ids,
        yes_price=yes_price,
        yes_token_id=yes_token_id,
        best_bid=_as_optional_float(raw.get("bestBid")),
        best_ask=_as_optional_float(raw.get("bestAsk")),
        last_trade_price=_as_optional_float(raw.get("lastTradePrice")),
        one_day_price_change=_as_optional_float(raw.get("oneDayPriceChange")),
        volume=_as_float(raw.get("volume")),
        volume_24hr=_as_float(raw.get("volume24hr")),
        liquidity=_as_float(raw.get("liquidity")),
        end_date=raw.get("endDate"),
        active=bool(raw.get("active", False)),
        closed=bool(raw.get("closed", False)),
        icon=raw.get("icon"),
    )


@dataclass
class Position:
    """An open position held by a wallet."""

    title: str
    outcome: str
    size: float
    avg_price: float
    cur_price: float
    current_value: float
    cash_pnl: float
    percent_pnl: float
    slug: str
    end_date: str | None


def parse_position(raw: dict[str, Any]) -> Position:
    """Build a Position from a Data API `positions[]` entry."""
    return Position(
        title=str(raw.get("title", "")),
        outcome=str(raw.get("outcome", "")),
        size=_as_float(raw.get("size")),
        avg_price=_as_float(raw.get("avgPrice")),
        cur_price=_as_float(raw.get("curPrice")),
        current_value=_as_float(raw.get("currentValue")),
        cash_pnl=_as_float(raw.get("cashPnl")),
        percent_pnl=_as_float(raw.get("percentPnl")),
        slug=str(raw.get("slug", "")),
        end_date=raw.get("endDate"),
    )


def parse_portfolio_value(raw: Any) -> float:
    """Read the wallet value from the Data API `/value` array response."""
    if isinstance(raw, list) and raw:
        return _as_float(raw[0].get("value"))
    return 0.0


@dataclass
class Portfolio:
    """Aggregated wallet portfolio."""

    wallet: str
    value: float
    positions: list[Position]

    @property
    def position_count(self) -> int:
        """Number of open positions."""
        return len(self.positions)

    @property
    def total_cash_pnl(self) -> float:
        """Sum of unrealized cash P&L across all positions."""
        return round(sum(p.cash_pnl for p in self.positions), 2)

    @property
    def largest_position(self) -> Position | None:
        """The position with the greatest current value, if any."""
        if not self.positions:
            return None
        return max(self.positions, key=lambda p: p.current_value)
