"""Pure data models and parsers for Polymarket API payloads.

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


def parse_market(raw: dict[str, Any], *, event_title: str, event_slug: str) -> MarketInfo:
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


# ---------------------------------------------------------------------------
# Placeholder stubs — filled in during the position/portfolio TDD cycle.
# ---------------------------------------------------------------------------

def parse_position(raw: dict[str, Any]) -> Any:  # pragma: no cover
    """Stub: replaced in Step 8."""
    raise NotImplementedError("parse_position not yet implemented")


def parse_portfolio_value(raw: Any) -> float:  # pragma: no cover
    """Stub: replaced in Step 8."""
    raise NotImplementedError("parse_portfolio_value not yet implemented")
