# Polymarket Home Assistant Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the `integration_blueprint` template into a read-only `polymarket` custom integration that surfaces, per config entry, the top markets in a chosen Polymarket category (live odds, volume, liquidity, resolution) plus an optional wallet portfolio (value, positions, P&L) — exposing the maximum data Polymarket's public APIs offer as HA sensors and binary sensors.

**Architecture:** A single `DataUpdateCoordinator` polls three public Polymarket APIs every 15 min (configurable): **Gamma** (`gamma-api.polymarket.com`) for category events/markets and their odds, **CLOB** (`clob.polymarket.com`) for a live midpoint per market's YES token, and **Data** (`data-api.polymarket.com`) for the optional wallet's value and positions. Raw JSON is normalized into pure dataclasses in `models.py` (the unit-tested core), the coordinator exposes one `PolymarketCoordinatorData`, and platforms build one HA device per market plus one portfolio device. No auth, no private keys, no trading — read-only.

**Tech Stack:** Python 3.13, Home Assistant 2025.2.4 integration APIs (`config_entries`, `DataUpdateCoordinator`, `SensorEntity`, `BinarySensorEntity`, `selector`), `aiohttp` + `async_timeout` (bundled with HA), `voluptuous`, `pytest` (pure-model TDD, no HA test harness needed for the core loop), `ruff` (lint `ALL`).

---

## Polymarket API Reference (verified 2026-05-29)

These shapes are confirmed against live endpoints — code below depends on them.

**Resolve a category slug → tag id** — `GET https://gamma-api.polymarket.com/tags/slug/<slug>`
```json
{ "id": "2", "label": "Politics", "slug": "politics" }
```
Known stable categories: `politics`(2), `sports`(1), `crypto`(21), `economy`(100328).

**Top events in a category** — `GET https://gamma-api.polymarket.com/events?limit=<N>&order=volume24hr&ascending=false&closed=false&tag_id=<id>&related_tags=true`
Returns a JSON array of events; each event has a `markets` array. Each **market** object includes:
```json
{
  "id": "1919425",
  "question": "US x Iran permanent peace deal by May 31, 2026?",
  "slug": "us-x-iran-permanent-peace-deal-...",
  "outcomes": "[\"Yes\", \"No\"]",
  "outcomePrices": "[\"0.125\", \"0.875\"]",
  "clobTokenIds": "[\"7209...92\", \"4291...16\"]",
  "volume": "73718769.31", "volume24hr": 6875124.59, "liquidity": "899934.12",
  "bestBid": 0.12, "bestAsk": 0.13, "lastTradePrice": 0.13,
  "oneDayPriceChange": 0.01, "endDate": "2026-05-31T00:00:00Z",
  "active": true, "closed": false, "icon": "https://...jpg"
}
```
> NOTE: `outcomes`, `outcomePrices`, `clobTokenIds` are **JSON-encoded strings**, not arrays — they must be `json.loads`-ed. `volume`/`liquidity` may arrive as strings; `volume24hr`/`bestBid`/etc. as numbers. Parsing must tolerate both and tolerate missing keys.

**Live midpoint for a token** — `GET https://clob.polymarket.com/midpoint?token_id=<id>` → `{"mid":"0.14"}`

**Wallet portfolio value** — `GET https://data-api.polymarket.com/value?user=<0x...>` → `[{"user":"0x...","value":720942.30}]`

**Wallet positions** — `GET https://data-api.polymarket.com/positions?user=<0x...>&sortBy=CURRENT&sortDirection=DESC&limit=<N>`
```json
[{ "title": "Will the U.S. invade Iran before 2027?", "outcome": "No",
   "size": 225642.18, "avgPrice": 0.6721, "curPrice": 0.825,
   "currentValue": 186154.79, "cashPnl": 34495.49, "percentPnl": 22.74,
   "slug": "will-the-us-invade-iran-before-2027", "endDate": "2026-12-31" }]
```

---

## File Structure

All code lives under `custom_components/polymarket/` (renamed from `integration_blueprint/`). Tests live under `tests/`.

| File | Responsibility |
|------|----------------|
| `custom_components/polymarket/const.py` | Domain, API base URLs, CONF keys, defaults, category list, attribution |
| `custom_components/polymarket/models.py` | **Pure** dataclasses + parse functions (`MarketInfo`, `Position`, `Portfolio`, `parse_market`, `parse_position`, `parse_portfolio_value`). No HA/network imports. Fully unit-tested. |
| `custom_components/polymarket/api.py` | `PolymarketApiClient` — async HTTP against Gamma/CLOB/Data; returns parsed models. Custom error classes. |
| `custom_components/polymarket/data.py` | `PolymarketConfigEntry` type, `PolymarketRuntimeData`, `PolymarketCoordinatorData` (coordinator payload). |
| `custom_components/polymarket/coordinator.py` | `PolymarketDataUpdateCoordinator` — orchestrates one poll into `PolymarketCoordinatorData`. |
| `custom_components/polymarket/config_flow.py` | User step (optional wallet, category select, top N) + options flow (top N, scan interval). |
| `custom_components/polymarket/entity.py` | `PolymarketMarketEntity` + `PolymarketPortfolioEntity` base classes (device grouping). |
| `custom_components/polymarket/sensor.py` | Per-market sensors + portfolio sensors. |
| `custom_components/polymarket/binary_sensor.py` | Per-market "resolved/closed" binary sensor. |
| `custom_components/polymarket/__init__.py` | Entry setup/unload/reload, platform list. |
| `custom_components/polymarket/manifest.json` | Domain `polymarket`, metadata. |
| `custom_components/polymarket/translations/en.json` | Config/options flow strings. |
| `tests/test_models.py` | TDD for all parse functions (pytest only). |
| `tests/test_api.py` | TDD for `PolymarketApiClient` against a fake aiohttp session (pytest only, `asyncio.run`). |
| `tests/fixtures/*.json` | Captured API responses used by tests. |
| `requirements.test.txt` | `pytest` for the core loop. |

The blueprint's `switch.py` is **deleted** (read-only integration — no actions).

---

### Task 0: Scaffold — rename blueprint → polymarket, add test deps

**Files:**
- Rename dir: `custom_components/integration_blueprint/` → `custom_components/polymarket/`
- Delete: `custom_components/polymarket/switch.py`
- Modify: `custom_components/polymarket/manifest.json`
- Create: `requirements.test.txt`
- Create: `tests/__init__.py`, `tests/fixtures/` (dir)

- [ ] **Step 1: Rename the component directory and drop the switch platform**

```bash
cd /Users/hudsonbrendon/ha-polymarket
git mv custom_components/integration_blueprint custom_components/polymarket
git rm custom_components/polymarket/switch.py
```

- [ ] **Step 2: Replace the manifest**

Overwrite `custom_components/polymarket/manifest.json` with:

```json
{
  "domain": "polymarket",
  "name": "Polymarket",
  "codeowners": [
    "@hudsonbrendon"
  ],
  "config_flow": true,
  "documentation": "https://github.com/hudsonbrendon/ha-polymarket",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/hudsonbrendon/ha-polymarket/issues",
  "integration_type": "service",
  "version": "0.1.0"
}
```

- [ ] **Step 3: Create the test requirements file**

Create `requirements.test.txt`:

```text
pytest==8.3.4
```

> The core TDD loop (`models.py`, `api.py`) imports no Home Assistant code, so plain `pytest` runs it. HA-glue files are verified by loading the integration in HA (Task 12).

- [ ] **Step 4: Create the tests package**

Create `tests/__init__.py`:

```python
"""Tests for the Polymarket integration."""
```

Create the fixtures directory:

```bash
mkdir -p tests/fixtures
```

- [ ] **Step 5: Install test deps and verify pytest runs (collecting nothing yet)**

Run:
```bash
python3 -m pip install --requirement requirements.test.txt
python3 -m pytest tests/ -q
```
Expected: `no tests ran` (exit code 5) — confirms pytest is installed and `tests/` is importable.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold polymarket integration from blueprint, add pytest"
```

---

### Task 1: Constants

**Files:**
- Create (overwrite): `custom_components/polymarket/const.py`

- [ ] **Step 1: Write the constants module**

Overwrite `custom_components/polymarket/const.py`:

```python
"""Constants for the Polymarket integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "polymarket"
ATTRIBUTION = "Data provided by Polymarket"

# Public API base URLs (no auth required).
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
DATA_BASE = "https://data-api.polymarket.com"

# Config / options keys.
CONF_WALLET_ADDRESS = "wallet_address"
CONF_CATEGORY = "category"
CONF_TOP_N = "top_n"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults.
DEFAULT_CATEGORY = "politics"
DEFAULT_TOP_N = 5
MIN_TOP_N = 1
MAX_TOP_N = 25
DEFAULT_SCAN_INTERVAL = 15  # minutes
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 360

# Curated categories offered in the config flow (slug -> label).
# Users may type any other Polymarket tag slug (custom_value is enabled).
CATEGORIES: dict[str, str] = {
    "politics": "Politics",
    "sports": "Sports",
    "crypto": "Crypto",
    "economy": "Economy",
    "tech": "Tech",
    "pop-culture": "Pop Culture",
    "world": "World",
}
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/polymarket/const.py
git commit -m "feat: add polymarket constants"
```

---

### Task 2: Models — pure parsing (TDD)

**Files:**
- Create: `custom_components/polymarket/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test for `parse_market`**

Create `tests/test_models.py`:

```python
"""Tests for Polymarket model parsing (pure, no HA, no network)."""

from custom_components.polymarket.models import (
    parse_market,
    parse_portfolio_value,
    parse_position,
)

RAW_MARKET = {
    "id": "1919425",
    "question": "US x Iran permanent peace deal by May 31, 2026?",
    "slug": "us-x-iran-permanent-peace-deal",
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.125", "0.875"]',
    "clobTokenIds": '["72094", "42918"]',
    "volume": "73718769.31",
    "volume24hr": 6875124.59,
    "liquidity": "899934.12",
    "bestBid": 0.12,
    "bestAsk": 0.13,
    "lastTradePrice": 0.13,
    "oneDayPriceChange": 0.01,
    "endDate": "2026-05-31T00:00:00Z",
    "active": True,
    "closed": False,
    "icon": "https://example.com/icon.jpg",
}


def test_parse_market_extracts_core_fields():
    market = parse_market(RAW_MARKET, event_title="US/Iran", event_slug="us-iran")
    assert market.market_id == "1919425"
    assert market.question == "US x Iran permanent peace deal by May 31, 2026?"
    assert market.event_title == "US/Iran"
    assert market.outcomes == ["Yes", "No"]
    assert market.prices == [0.125, 0.875]
    assert market.clob_token_ids == ["72094", "42918"]
    assert market.volume == 73718769.31
    assert market.volume_24hr == 6875124.59
    assert market.liquidity == 899934.12
    assert market.closed is False


def test_parse_market_yes_price_matches_yes_outcome():
    market = parse_market(RAW_MARKET, event_title="x", event_slug="x")
    # "Yes" is index 0, so yes_price is the first price.
    assert market.yes_price == 0.125
    assert market.yes_token_id == "72094"


def test_parse_market_yes_price_when_yes_is_second():
    raw = {
        **RAW_MARKET,
        "outcomes": '["No", "Yes"]',
        "outcomePrices": '["0.30", "0.70"]',
        "clobTokenIds": '["AAA", "BBB"]',
    }
    market = parse_market(raw, event_title="x", event_slug="x")
    assert market.yes_price == 0.70
    assert market.yes_token_id == "BBB"


def test_parse_market_tolerates_missing_and_malformed_fields():
    market = parse_market(
        {"id": "9", "question": "Q?"}, event_title="x", event_slug="x"
    )
    assert market.market_id == "9"
    assert market.outcomes == []
    assert market.prices == []
    assert market.yes_price is None
    assert market.volume == 0.0
    assert market.clob_token_ids == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.polymarket.models'`

- [ ] **Step 3: Implement `models.py` market parsing**

Create `custom_components/polymarket/models.py`:

```python
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
```

- [ ] **Step 4: Run the market tests to verify they pass**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/polymarket/models.py tests/test_models.py
git commit -m "feat: add market parsing with TDD"
```

- [ ] **Step 6: Write the failing tests for position + portfolio parsing**

Append to `tests/test_models.py`:

```python
RAW_POSITION = {
    "title": "Will the U.S. invade Iran before 2027?",
    "outcome": "No",
    "size": 225642.18,
    "avgPrice": 0.6721,
    "curPrice": 0.825,
    "currentValue": 186154.79,
    "cashPnl": 34495.49,
    "percentPnl": 22.74,
    "slug": "will-the-us-invade-iran-before-2027",
    "endDate": "2026-12-31",
}


def test_parse_position_extracts_fields():
    pos = parse_position(RAW_POSITION)
    assert pos.title == "Will the U.S. invade Iran before 2027?"
    assert pos.outcome == "No"
    assert pos.size == 225642.18
    assert pos.cur_price == 0.825
    assert pos.current_value == 186154.79
    assert pos.cash_pnl == 34495.49
    assert pos.percent_pnl == 22.74
    assert pos.slug == "will-the-us-invade-iran-before-2027"


def test_parse_position_tolerates_missing_fields():
    pos = parse_position({"title": "Q"})
    assert pos.title == "Q"
    assert pos.size == 0.0
    assert pos.current_value == 0.0
    assert pos.outcome == ""


def test_parse_portfolio_value_reads_first_entry():
    assert parse_portfolio_value([{"user": "0xabc", "value": 720942.30}]) == 720942.30


def test_parse_portfolio_value_handles_empty():
    assert parse_portfolio_value([]) == 0.0
    assert parse_portfolio_value(None) == 0.0
```

- [ ] **Step 7: Run to verify the new tests fail**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: FAIL — `ImportError: cannot import name 'parse_position'`

- [ ] **Step 8: Implement position + portfolio parsing**

Append to `custom_components/polymarket/models.py`:

```python
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
```

- [ ] **Step 9: Run all model tests to verify they pass**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: PASS (8 passed)

- [ ] **Step 10: Add and run a test for the `Portfolio` aggregates**

Append to `tests/test_models.py`:

```python
from custom_components.polymarket.models import Portfolio


def _pos(value: float, pnl: float) -> "object":
    return parse_position(
        {"title": "t", "currentValue": value, "cashPnl": pnl, "size": 1}
    )


def test_portfolio_aggregates():
    portfolio = Portfolio(
        wallet="0xabc",
        value=1000.0,
        positions=[_pos(600.0, 50.0), _pos(400.0, -10.0)],
    )
    assert portfolio.position_count == 2
    assert portfolio.total_cash_pnl == 40.0
    assert portfolio.largest_position.current_value == 600.0


def test_portfolio_empty_largest_is_none():
    portfolio = Portfolio(wallet="0xabc", value=0.0, positions=[])
    assert portfolio.largest_position is None
```

Run: `python3 -m pytest tests/test_models.py -q`
Expected: PASS (10 passed)

- [ ] **Step 11: Commit**

```bash
git add custom_components/polymarket/models.py tests/test_models.py
git commit -m "feat: add position and portfolio parsing with TDD"
```

---

### Task 3: API client (TDD with a fake session)

**Files:**
- Create (overwrite): `custom_components/polymarket/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing test for category-markets fetching**

Create `tests/test_api.py`:

```python
"""Tests for PolymarketApiClient using a fake aiohttp session (no network)."""

import asyncio
from typing import Any

from custom_components.polymarket.api import (
    PolymarketApiClient,
    PolymarketApiClientError,
)


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    async def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status >= 400:
            msg = f"HTTP {self.status}"
            raise RuntimeError(msg)

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class _FakeSession:
    """Records requests and returns queued responses keyed by URL substring."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self._routes = routes
        self.requested: list[str] = []

    def request(self, method: str, url: str, **_: Any) -> _FakeResponse:
        self.requested.append(url)
        for needle, payload in self._routes.items():
            if needle in url:
                return _FakeResponse(payload)
        return _FakeResponse([], status=404)


TAG_PAYLOAD = {"id": "2", "label": "Politics", "slug": "politics"}
EVENTS_PAYLOAD = [
    {
        "title": "US/Iran",
        "slug": "us-iran",
        "markets": [
            {
                "id": "1",
                "question": "Q1?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.4", "0.6"]',
                "clobTokenIds": '["T1", "T2"]',
                "volume24hr": 100.0,
            }
        ],
    }
]


def test_get_category_markets_resolves_tag_then_fetches_events():
    session = _FakeSession(
        {"/tags/slug/politics": TAG_PAYLOAD, "/events": EVENTS_PAYLOAD}
    )
    client = PolymarketApiClient(session=session)
    markets = asyncio.run(client.async_get_category_markets("politics", top_n=5))

    assert len(markets) == 1
    assert markets[0].question == "Q1?"
    assert markets[0].event_title == "US/Iran"
    assert markets[0].yes_price == 0.4
    # tag_id=2 must be forwarded to the events call.
    assert any("tag_id=2" in url for url in session.requested)
    assert any("limit=5" in url for url in session.requested)


def test_get_category_markets_unknown_tag_raises():
    session = _FakeSession({"/tags/slug/nope": {}, "/events": []})
    client = PolymarketApiClient(session=session)
    try:
        asyncio.run(client.async_get_category_markets("nope", top_n=5))
    except PolymarketApiClientError:
        return
    raise AssertionError("expected PolymarketApiClientError for unknown tag")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_api.py -q`
Expected: FAIL — `ImportError: cannot import name 'PolymarketApiClient'`

- [ ] **Step 3: Implement the API client**

Overwrite `custom_components/polymarket/api.py`:

```python
"""Async client for Polymarket's public Gamma, CLOB, and Data APIs."""

from __future__ import annotations

import asyncio
import socket
from typing import TYPE_CHECKING, Any

import aiohttp
import async_timeout

from .const import CLOB_BASE, DATA_BASE, GAMMA_BASE
from .models import (
    MarketInfo,
    Portfolio,
    parse_market,
    parse_portfolio_value,
    parse_position,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_TIMEOUT = 15


class PolymarketApiClientError(Exception):
    """General Polymarket API error."""


class PolymarketApiClientCommunicationError(PolymarketApiClientError):
    """Network/communication error."""


class PolymarketApiClient:
    """Read-only client for Polymarket public APIs."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Store the shared aiohttp session."""
        self._session = session

    async def async_resolve_tag_id(self, category: str) -> str:
        """Resolve a category slug to its Gamma tag id."""
        payload = await self._get(f"{GAMMA_BASE}/tags/slug/{category}")
        tag_id = payload.get("id") if isinstance(payload, dict) else None
        if not tag_id:
            msg = f"Unknown Polymarket category '{category}'"
            raise PolymarketApiClientError(msg)
        return str(tag_id)

    async def async_get_category_markets(
        self, category: str, top_n: int
    ) -> list[MarketInfo]:
        """Return the top `top_n` open markets in a category, by 24h volume."""
        tag_id = await self.async_resolve_tag_id(category)
        events = await self._get(
            f"{GAMMA_BASE}/events",
            params={
                "limit": top_n,
                "order": "volume24hr",
                "ascending": "false",
                "closed": "false",
                "tag_id": tag_id,
                "related_tags": "true",
            },
        )
        markets: list[MarketInfo] = []
        for event in events if isinstance(events, list) else []:
            event_title = str(event.get("title", ""))
            event_slug = str(event.get("slug", ""))
            for raw_market in event.get("markets", []) or []:
                markets.append(
                    parse_market(
                        raw_market, event_title=event_title, event_slug=event_slug
                    )
                )
        return markets[:top_n]

    async def async_get_midpoint(self, token_id: str) -> float | None:
        """Return the CLOB midpoint for a token, or None on failure."""
        try:
            payload = await self._get(
                f"{CLOB_BASE}/midpoint", params={"token_id": token_id}
            )
        except PolymarketApiClientError:
            return None
        if isinstance(payload, dict) and payload.get("mid") is not None:
            try:
                return float(payload["mid"])
            except (TypeError, ValueError):
                return None
        return None

    async def async_get_portfolio(self, wallet: str, top_n: int = 25) -> Portfolio:
        """Return a wallet's value and its top positions by current value."""
        value_payload = await self._get(
            f"{DATA_BASE}/value", params={"user": wallet}
        )
        positions_payload = await self._get(
            f"{DATA_BASE}/positions",
            params={
                "user": wallet,
                "sortBy": "CURRENT",
                "sortDirection": "DESC",
                "limit": top_n,
            },
        )
        positions = [
            parse_position(raw)
            for raw in (positions_payload if isinstance(positions_payload, list) else [])
        ]
        return Portfolio(
            wallet=wallet,
            value=parse_portfolio_value(value_payload),
            positions=positions,
        )

    async def _get(
        self, url: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        """Perform a GET request and return parsed JSON."""
        try:
            async with async_timeout.timeout(_TIMEOUT):
                async with self._session.request(
                    method="get", url=url, params=params
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except (TimeoutError, asyncio.TimeoutError) as exception:
            msg = f"Timeout fetching {url}"
            raise PolymarketApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching {url}: {exception}"
            raise PolymarketApiClientCommunicationError(msg) from exception
        except PolymarketApiClientError:
            raise
        except Exception as exception:  # noqa: BLE001
            msg = f"Unexpected error fetching {url}: {exception}"
            raise PolymarketApiClientError(msg) from exception
```

> NOTE: the fake session in the test passes `params=` through `request(...)` but builds the URL without query string. The test asserts `tag_id=2`/`limit=5` appear in the requested URL, so the client must encode params into the URL the fake records. aiohttp normally appends params itself; the fake does not. To make the assertion meaningful **and** keep real behavior, the fake is updated in the next step to mirror aiohttp by appending params.

- [ ] **Step 4: Update the fake session to append params (so URL assertions are real)**

In `tests/test_api.py`, replace the `_FakeSession.request` method with:

```python
    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        params = kwargs.get("params") or {}
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        self.requested.append(url)
        for needle, payload in self._routes.items():
            if needle in url:
                return _FakeResponse(payload)
        return _FakeResponse([], status=404)
```

- [ ] **Step 5: Run the API tests to verify they pass**

Run: `python3 -m pytest tests/test_api.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Add a test for portfolio fetching, run, verify pass**

Append to `tests/test_api.py`:

```python
VALUE_PAYLOAD = [{"user": "0xabc", "value": 1234.5}]
POSITIONS_PAYLOAD = [
    {"title": "P1", "currentValue": 900.0, "cashPnl": 100.0, "outcome": "Yes"},
    {"title": "P2", "currentValue": 300.0, "cashPnl": -20.0, "outcome": "No"},
]


def test_get_portfolio_builds_value_and_positions():
    session = _FakeSession({"/value": VALUE_PAYLOAD, "/positions": POSITIONS_PAYLOAD})
    client = PolymarketApiClient(session=session)
    portfolio = asyncio.run(client.async_get_portfolio("0xabc"))

    assert portfolio.value == 1234.5
    assert portfolio.position_count == 2
    assert portfolio.total_cash_pnl == 80.0
    assert portfolio.largest_position.title == "P1"


def test_get_midpoint_parses_mid():
    session = _FakeSession({"/midpoint": {"mid": "0.42"}})
    client = PolymarketApiClient(session=session)
    assert asyncio.run(client.async_get_midpoint("T1")) == 0.42
```

Run: `python3 -m pytest tests/test_api.py -q`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add custom_components/polymarket/api.py tests/test_api.py
git commit -m "feat: add Polymarket API client with TDD"
```

---

### Task 4: Runtime data types

**Files:**
- Create (overwrite): `custom_components/polymarket/data.py`

- [ ] **Step 1: Write the data module**

Overwrite `custom_components/polymarket/data.py`:

```python
"""Runtime data structures for the Polymarket integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import PolymarketApiClient
    from .coordinator import PolymarketDataUpdateCoordinator
    from .models import MarketInfo, Portfolio


@dataclass
class PolymarketCoordinatorData:
    """Payload produced by the coordinator on each poll."""

    markets: list[MarketInfo]
    portfolio: Portfolio | None


@dataclass
class PolymarketRuntimeData:
    """Data stored on the config entry's runtime_data."""

    client: PolymarketApiClient
    coordinator: PolymarketDataUpdateCoordinator
    integration: Integration


type PolymarketConfigEntry = ConfigEntry[PolymarketRuntimeData]
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/polymarket/data.py
git commit -m "feat: add runtime data types"
```

---

### Task 5: Coordinator

**Files:**
- Create (overwrite): `custom_components/polymarket/coordinator.py`

- [ ] **Step 1: Write the coordinator**

Overwrite `custom_components/polymarket/coordinator.py`:

```python
"""DataUpdateCoordinator for the Polymarket integration."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PolymarketApiClientError
from .const import (
    CONF_CATEGORY,
    CONF_TOP_N,
    CONF_WALLET_ADDRESS,
    DEFAULT_CATEGORY,
    DEFAULT_TOP_N,
    LOGGER,
)
from .data import PolymarketCoordinatorData

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant

    from .api import PolymarketApiClient
    from .data import PolymarketConfigEntry


class PolymarketDataUpdateCoordinator(DataUpdateCoordinator[PolymarketCoordinatorData]):
    """Polls Polymarket and produces a PolymarketCoordinatorData."""

    config_entry: PolymarketConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: PolymarketApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name="polymarket",
            update_interval=update_interval,
        )
        self._client = client

    def _options(self) -> dict:
        """Merged entry data + options (options win)."""
        return {**self.config_entry.data, **self.config_entry.options}

    async def _async_update_data(self) -> PolymarketCoordinatorData:
        """Fetch category markets (+ live midpoints) and optional portfolio."""
        options = self._options()
        category = options.get(CONF_CATEGORY, DEFAULT_CATEGORY)
        top_n = int(options.get(CONF_TOP_N, DEFAULT_TOP_N))
        wallet = options.get(CONF_WALLET_ADDRESS)

        try:
            markets = await self._client.async_get_category_markets(category, top_n)
        except PolymarketApiClientError as exception:
            raise UpdateFailed(exception) from exception

        # Enrich each market's YES token with a live CLOB midpoint.
        # top_n is user-bounded (<=25), so this fan-out is small.
        async def _fill_midpoint(market) -> None:  # noqa: ANN001
            if market.yes_token_id:
                market.midpoint = await self._client.async_get_midpoint(
                    market.yes_token_id
                )

        await asyncio.gather(*(_fill_midpoint(m) for m in markets))

        portfolio = None
        if wallet:
            try:
                portfolio = await self._client.async_get_portfolio(wallet)
            except PolymarketApiClientError as exception:
                # A bad wallet shouldn't kill market data — log and continue.
                LOGGER.warning("Failed to fetch portfolio for %s: %s", wallet, exception)

        return PolymarketCoordinatorData(markets=markets, portfolio=portfolio)
```

> NOTE: `ConfigEntryError` import is retained for forward use; if ruff flags it as unused, delete the import line. The wallet failure is intentionally non-fatal so market sensors stay available.

- [ ] **Step 2: Remove the unused import flagged by lint**

Run: `scripts/lint` (ruff). If it reports `F401` for `ConfigEntryError`, delete this line from `coordinator.py`:

```python
from homeassistant.exceptions import ConfigEntryError
```

Re-run `scripts/lint` until `coordinator.py` is clean.

- [ ] **Step 3: Commit**

```bash
git add custom_components/polymarket/coordinator.py
git commit -m "feat: add coordinator polling markets and portfolio"
```

---

### Task 6: Config flow + options flow

**Files:**
- Create (overwrite): `custom_components/polymarket/config_flow.py`

- [ ] **Step 1: Write the config flow**

Overwrite `custom_components/polymarket/config_flow.py`:

```python
"""Config and options flow for the Polymarket integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import PolymarketApiClient, PolymarketApiClientError
from .const import (
    CATEGORIES,
    CONF_CATEGORY,
    CONF_SCAN_INTERVAL,
    CONF_TOP_N,
    CONF_WALLET_ADDRESS,
    DEFAULT_CATEGORY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOP_N,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MAX_TOP_N,
    MIN_SCAN_INTERVAL,
    MIN_TOP_N,
)

_WALLET_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def _category_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=slug, label=label)
                for slug, label in CATEGORIES.items()
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
            custom_value=True,
        )
    )


def _top_n_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_TOP_N, max=MAX_TOP_N, step=1, mode=selector.NumberSelectorMode.BOX
        )
    )


def _scan_interval_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL,
            max=MAX_SCAN_INTERVAL,
            step=1,
            unit_of_measurement="min",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


class PolymarketFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect category, top N, and an optional wallet address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            wallet = (user_input.get(CONF_WALLET_ADDRESS) or "").strip()
            category = user_input[CONF_CATEGORY].strip().lower()
            if wallet and not _WALLET_RE.match(wallet):
                errors[CONF_WALLET_ADDRESS] = "invalid_wallet"
            if not errors:
                try:
                    await self._validate(category, wallet or None)
                except PolymarketApiClientError as exception:
                    LOGGER.warning("Validation failed: %s", exception)
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(
                        f"{category}:{wallet.lower() or 'no-wallet'}"
                    )
                    self._abort_if_unique_id_configured()
                    title = CATEGORIES.get(category, category.title())
                    if wallet:
                        title = f"{title} + wallet"
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_CATEGORY: category,
                            CONF_TOP_N: int(user_input[CONF_TOP_N]),
                            CONF_WALLET_ADDRESS: wallet,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CATEGORY, default=DEFAULT_CATEGORY
                    ): _category_selector(),
                    vol.Required(
                        CONF_TOP_N, default=DEFAULT_TOP_N
                    ): _top_n_selector(),
                    vol.Optional(CONF_WALLET_ADDRESS, default=""): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def _validate(self, category: str, wallet: str | None) -> None:
        """Hit the APIs once to confirm the category (and wallet) work."""
        client = PolymarketApiClient(
            session=async_create_clientsession(self.hass)
        )
        await client.async_get_category_markets(category, top_n=1)
        if wallet:
            await client.async_get_portfolio(wallet, top_n=1)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PolymarketOptionsFlow:
        """Return the options flow."""
        return PolymarketOptionsFlow()


class PolymarketOptionsFlow(config_entries.OptionsFlow):
    """Allow editing top N and scan interval after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOP_N,
                        default=current.get(CONF_TOP_N, DEFAULT_TOP_N),
                    ): _top_n_selector(),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): _scan_interval_selector(),
                }
            ),
        )
```

- [ ] **Step 2: Lint the config flow**

Run: `scripts/lint`
Expected: no errors for `config_flow.py` (fix any ruff complaints inline before continuing).

- [ ] **Step 3: Commit**

```bash
git add custom_components/polymarket/config_flow.py
git commit -m "feat: add config and options flow"
```

---

### Task 7: Base entities

**Files:**
- Create (overwrite): `custom_components/polymarket/entity.py`

- [ ] **Step 1: Write the entity base classes**

Overwrite `custom_components/polymarket/entity.py`:

```python
"""Base entities for the Polymarket integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN

if TYPE_CHECKING:
    from .coordinator import PolymarketDataUpdateCoordinator


class PolymarketMarketEntity(CoordinatorEntity[PolymarketDataUpdateCoordinator]):
    """Base entity for a single tracked market (one HA device per market)."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PolymarketDataUpdateCoordinator, market_id: str
    ) -> None:
        """Bind the entity to a market id and build its device."""
        super().__init__(coordinator)
        self._market_id = market_id
        entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{market_id}")},
            manufacturer="Polymarket",
            model="Market",
            name=self._market.question if self._market else market_id,
            configuration_url=(
                f"https://polymarket.com/event/{self._market.event_slug}"
                if self._market and self._market.event_slug
                else "https://polymarket.com"
            ),
        )

    @property
    def _market(self):  # noqa: ANN202
        """Return the current MarketInfo for this entity, or None if gone."""
        data = self.coordinator.data
        if not data:
            return None
        for market in data.markets:
            if market.market_id == self._market_id:
                return market
        return None

    @property
    def available(self) -> bool:
        """Available only while the market is still in the tracked set."""
        return super().available and self._market is not None


class PolymarketPortfolioEntity(CoordinatorEntity[PolymarketDataUpdateCoordinator]):
    """Base entity for the wallet portfolio (one HA device)."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: PolymarketDataUpdateCoordinator) -> None:
        """Build the portfolio device."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_portfolio")},
            manufacturer="Polymarket",
            model="Portfolio",
            name="Polymarket Portfolio",
            configuration_url="https://polymarket.com/portfolio",
        )

    @property
    def _portfolio(self):  # noqa: ANN202
        """Return the current Portfolio, or None."""
        return self.coordinator.data.portfolio if self.coordinator.data else None
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/polymarket/entity.py
git commit -m "feat: add base market and portfolio entities"
```

---

### Task 8: Market sensors

**Files:**
- Create (overwrite): `custom_components/polymarket/sensor.py`

- [ ] **Step 1: Write the sensor platform (market sensors only for now)**

Overwrite `custom_components/polymarket/sensor.py`:

```python
"""Sensor platform for the Polymarket integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from .entity import PolymarketMarketEntity, PolymarketPortfolioEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PolymarketDataUpdateCoordinator
    from .data import PolymarketConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: PolymarketConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Polymarket sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = []

    for market in coordinator.data.markets:
        entities.append(MarketOddsSensor(coordinator, market.market_id))
        entities.append(MarketVolumeSensor(coordinator, market.market_id))
        entities.append(MarketLiquiditySensor(coordinator, market.market_id))

    if coordinator.data.portfolio is not None:
        entities.append(PortfolioValueSensor(coordinator))
        entities.append(PortfolioPnlSensor(coordinator))
        entities.append(PortfolioPositionsSensor(coordinator))

    async_add_entities(entities)


class MarketOddsSensor(PolymarketMarketEntity, SensorEntity):
    """YES probability for a market, as a percentage, with full detail attributes."""

    _attr_icon = "mdi:chart-line"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, market_id: str) -> None:  # noqa: ANN001
        """Init the odds sensor."""
        super().__init__(coordinator, market_id)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{market_id}_odds"
        self._attr_name = "YES odds"

    @property
    def native_value(self) -> float | None:
        """YES probability as a percent (prefers live CLOB midpoint)."""
        market = self._market
        if market is None:
            return None
        price = market.midpoint if market.midpoint is not None else market.yes_price
        return round(price * 100, 2) if price is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the maximum available market detail."""
        market = self._market
        if market is None:
            return {}
        return {
            "question": market.question,
            "event_title": market.event_title,
            "outcomes": market.outcomes,
            "outcome_prices": market.prices,
            "yes_price": market.yes_price,
            "midpoint": market.midpoint,
            "best_bid": market.best_bid,
            "best_ask": market.best_ask,
            "last_trade_price": market.last_trade_price,
            "one_day_price_change": market.one_day_price_change,
            "volume_total": market.volume,
            "volume_24hr": market.volume_24hr,
            "liquidity": market.liquidity,
            "end_date": market.end_date,
            "active": market.active,
            "closed": market.closed,
            "url": f"https://polymarket.com/event/{market.event_slug}",
            "icon_url": market.icon,
        }


class MarketVolumeSensor(PolymarketMarketEntity, SensorEntity):
    """24h trading volume for a market, in USD."""

    _attr_icon = "mdi:cash-multiple"
    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, market_id: str) -> None:  # noqa: ANN001
        """Init the volume sensor."""
        super().__init__(coordinator, market_id)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{market_id}_vol24"
        self._attr_name = "24h volume"

    @property
    def native_value(self) -> float | None:
        """Return 24h volume."""
        return self._market.volume_24hr if self._market else None


class MarketLiquiditySensor(PolymarketMarketEntity, SensorEntity):
    """Order-book liquidity for a market, in USD."""

    _attr_icon = "mdi:water"
    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, market_id: str) -> None:  # noqa: ANN001
        """Init the liquidity sensor."""
        super().__init__(coordinator, market_id)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{market_id}_liq"
        self._attr_name = "Liquidity"

    @property
    def native_value(self) -> float | None:
        """Return liquidity."""
        return self._market.liquidity if self._market else None
```

> NOTE: the portfolio sensor classes (`PortfolioValueSensor`, `PortfolioPnlSensor`, `PortfolioPositionsSensor`) are referenced in `async_setup_entry` but defined in Task 9. Implement Task 9 before loading in HA; the file will not import cleanly until then. (Tasks 8 and 9 together produce one working `sensor.py` — they are split only for review granularity.)

- [ ] **Step 2: Commit (work-in-progress sensor module)**

```bash
git add custom_components/polymarket/sensor.py
git commit -m "feat: add market odds, volume, liquidity sensors"
```

---

### Task 9: Portfolio sensors

**Files:**
- Modify: `custom_components/polymarket/sensor.py` (append portfolio sensor classes)

- [ ] **Step 1: Append the portfolio sensor classes**

Append to `custom_components/polymarket/sensor.py`:

```python
class PortfolioValueSensor(PolymarketPortfolioEntity, SensorEntity):
    """Total wallet portfolio value, in USD."""

    _attr_icon = "mdi:wallet"
    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        """Init the portfolio value sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_portfolio_value"
        self._attr_name = "Value"

    @property
    def native_value(self) -> float | None:
        """Return total portfolio value."""
        return round(self._portfolio.value, 2) if self._portfolio else None


class PortfolioPnlSensor(PolymarketPortfolioEntity, SensorEntity):
    """Total unrealized cash P&L across open positions, in USD."""

    _attr_icon = "mdi:chart-line-variant"
    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        """Init the P&L sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_portfolio_pnl"
        self._attr_name = "Unrealized P&L"

    @property
    def native_value(self) -> float | None:
        """Return total unrealized cash P&L."""
        return self._portfolio.total_cash_pnl if self._portfolio else None


class PortfolioPositionsSensor(PolymarketPortfolioEntity, SensorEntity):
    """Open position count, with the full position list as attributes."""

    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:  # noqa: ANN001
        """Init the positions sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_portfolio_positions"
        )
        self._attr_name = "Open positions"

    @property
    def native_value(self) -> int | None:
        """Return the number of open positions."""
        return self._portfolio.position_count if self._portfolio else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose each position and the largest holding."""
        portfolio = self._portfolio
        if portfolio is None:
            return {}
        largest = portfolio.largest_position
        return {
            "positions": [
                {
                    "title": p.title,
                    "outcome": p.outcome,
                    "size": p.size,
                    "avg_price": p.avg_price,
                    "current_price": p.cur_price,
                    "current_value": p.current_value,
                    "cash_pnl": p.cash_pnl,
                    "percent_pnl": p.percent_pnl,
                    "end_date": p.end_date,
                    "url": f"https://polymarket.com/event/{p.slug}",
                }
                for p in portfolio.positions
            ],
            "largest_position": largest.title if largest else None,
            "largest_position_value": largest.current_value if largest else None,
        }
```

- [ ] **Step 2: Lint the full sensor module**

Run: `scripts/lint`
Expected: no errors for `sensor.py`. Fix any ruff complaints inline.

- [ ] **Step 3: Commit**

```bash
git add custom_components/polymarket/sensor.py
git commit -m "feat: add portfolio value, pnl, and positions sensors"
```

---

### Task 10: Market binary sensor

**Files:**
- Create (overwrite): `custom_components/polymarket/binary_sensor.py`

- [ ] **Step 1: Write the binary sensor platform**

Overwrite `custom_components/polymarket/binary_sensor.py`:

```python
"""Binary sensor platform for the Polymarket integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import PolymarketMarketEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import PolymarketConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: PolymarketConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one 'resolved' binary sensor per tracked market."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MarketResolvedBinarySensor(coordinator, market.market_id)
        for market in coordinator.data.markets
    )


class MarketResolvedBinarySensor(PolymarketMarketEntity, BinarySensorEntity):
    """On when the market is closed/resolved."""

    _attr_icon = "mdi:gavel"

    def __init__(self, coordinator, market_id: str) -> None:  # noqa: ANN001
        """Init the resolved binary sensor."""
        super().__init__(coordinator, market_id)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{market_id}_resolved"
        )
        self._attr_name = "Resolved"

    @property
    def is_on(self) -> bool | None:
        """True when the market has closed."""
        market = self._market
        return market.closed if market else None
```

- [ ] **Step 2: Lint**

Run: `scripts/lint`
Expected: no errors for `binary_sensor.py`.

- [ ] **Step 3: Commit**

```bash
git add custom_components/polymarket/binary_sensor.py
git commit -m "feat: add market resolved binary sensor"
```

---

### Task 11: Entry setup wiring + translations

**Files:**
- Create (overwrite): `custom_components/polymarket/__init__.py`
- Create (overwrite): `custom_components/polymarket/translations/en.json`

- [ ] **Step 1: Write `__init__.py`**

Overwrite `custom_components/polymarket/__init__.py`:

```python
"""The Polymarket integration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import PolymarketApiClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import PolymarketDataUpdateCoordinator
from .data import PolymarketRuntimeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import PolymarketConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: PolymarketConfigEntry
) -> bool:
    """Set up Polymarket from a config entry."""
    client = PolymarketApiClient(session=async_get_clientsession(hass))

    scan_minutes = int(
        {**entry.data, **entry.options}.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    coordinator = PolymarketDataUpdateCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(minutes=scan_minutes),
    )
    entry.runtime_data = PolymarketRuntimeData(
        client=client,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PolymarketConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant, entry: PolymarketConfigEntry
) -> None:
    """Reload a config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
```

- [ ] **Step 2: Write the translations**

Overwrite `custom_components/polymarket/translations/en.json`:

```json
{
    "config": {
        "step": {
            "user": {
                "title": "Polymarket",
                "description": "Track the top markets in a Polymarket category, and optionally a wallet's portfolio. All data is read-only and public; no login is required.",
                "data": {
                    "category": "Category",
                    "top_n": "Number of markets to track",
                    "wallet_address": "Wallet address (optional, 0x...)"
                }
            }
        },
        "error": {
            "cannot_connect": "Could not reach Polymarket or the category was not found.",
            "invalid_wallet": "Wallet address must look like 0x followed by 40 hex characters."
        },
        "abort": {
            "already_configured": "This category and wallet combination is already configured."
        }
    },
    "options": {
        "step": {
            "init": {
                "title": "Polymarket options",
                "data": {
                    "top_n": "Number of markets to track",
                    "scan_interval": "Update interval (minutes)"
                }
            }
        }
    }
}
```

- [ ] **Step 3: Lint the whole package**

Run: `scripts/lint`
Expected: no errors across `custom_components/polymarket/`. Fix any inline.

- [ ] **Step 4: Run the full test suite**

Run: `python3 -m pytest tests/ -q`
Expected: PASS (all model + api tests green).

- [ ] **Step 5: Commit**

```bash
git add custom_components/polymarket/__init__.py custom_components/polymarket/translations/en.json
git commit -m "feat: wire up entry setup and translations"
```

---

### Task 12: Manual verification in Home Assistant + docs

**Files:**
- Modify: `README.md`
- Modify: `hacs.json` (name)
- Modify: `config/configuration.yaml` (logger domain)

- [ ] **Step 1: Point the dev logger at the new domain**

In `config/configuration.yaml`, replace:

```yaml
    custom_components.integration_blueprint: debug
```
with:
```yaml
    custom_components.polymarket: debug
```

- [ ] **Step 2: Update `hacs.json` name**

In `hacs.json`, replace `"name": "Integration blueprint"` with `"name": "Polymarket"`.

- [ ] **Step 3: Launch Home Assistant and add the integration**

Run:
```bash
scripts/develop
```
Then in a browser at `http://localhost:8123`:
1. Settings → Devices & Services → Add Integration → search **Polymarket**.
2. Pick category **Politics**, top N **5**, leave wallet blank → Submit.
3. Confirm 5 market devices appear, each with **YES odds (%)**, **24h volume (USD)**, **Liquidity (USD)**, and a **Resolved** binary sensor.
4. Open a YES-odds sensor → confirm the attributes block shows question, outcomes, prices, midpoint, bid/ask, volume, end date, URL.

Expected: entities populate within one refresh; logs show no errors under `custom_components.polymarket`.

- [ ] **Step 4: Verify the wallet path**

Remove the entry, re-add with a known public wallet address (e.g. `0x9d84ce0306f8551e02efef1680475fc0f1dc1344`) in the wallet field.
Expected: a **Polymarket Portfolio** device appears with **Value**, **Unrealized P&L**, and **Open positions** sensors; the positions sensor's attributes list each holding.

- [ ] **Step 5: Verify the options flow**

Settings → the Polymarket entry → Configure → change top N to 8 and interval to 10 → Submit.
Expected: the entry reloads and 8 markets are now tracked.

- [ ] **Step 6: Rewrite the README**

Overwrite `README.md` with project-accurate content:

```markdown
# Polymarket for Home Assistant

A read-only custom integration that surfaces [Polymarket](https://polymarket.com) data in Home Assistant: live odds, volume, and liquidity for the top markets in a category you choose, plus an optional wallet portfolio (value, open positions, and unrealized P&L).

## What you get

Per config entry you choose a **category** (Politics, Sports, Crypto, …) and how many top markets to track. For each market you get:

- **YES odds (%)** — live probability (prefers the CLOB midpoint), with full detail in attributes (outcomes, prices, best bid/ask, last trade, 24h change, volume, liquidity, end date, link).
- **24h volume (USD)** and **Liquidity (USD)** sensors.
- **Resolved** binary sensor — on when the market has closed.

Add a wallet address (optional) to also get a **Portfolio** device:

- **Value (USD)**, **Unrealized P&L (USD)**, and **Open positions** (count + per-position detail in attributes).

All data comes from Polymarket's public Gamma, CLOB, and Data APIs. No login, no private keys, no trading.

## Installation

Install via [HACS](https://hacs.xyz) as a custom repository, or copy `custom_components/polymarket` into your Home Assistant `config/custom_components/` directory and restart. Then add the **Polymarket** integration from Settings → Devices & Services.

## Configuration

Configured entirely through the UI: pick a category, set how many markets to track, and optionally paste a wallet address (`0x…`). The update interval and market count can be changed later under the integration's **Configure** options.

## Development

```bash
scripts/setup    # install runtime deps
scripts/develop  # run Home Assistant with this integration loaded
scripts/lint     # ruff
python3 -m pytest tests/ -q  # unit tests (models + API client)
```
```

- [ ] **Step 7: Final lint + test + commit**

```bash
scripts/lint
python3 -m pytest tests/ -q
git add -A
git commit -m "docs: rewrite README and finalize Polymarket integration"
```

---

## Self-Review

**Spec coverage** (user chose: market odds & prices ✓, personal portfolio ✓, trending/top markets ✓, selection by category/tag ✓, read-only ✓):
- Market odds & prices → `MarketOddsSensor` (state + rich attributes), Task 8. ✓
- Volume / liquidity → `MarketVolumeSensor`, `MarketLiquiditySensor`, Task 8. ✓
- Personal portfolio → wallet config (Task 6), `async_get_portfolio` (Task 3), portfolio sensors (Task 9). ✓
- Trending/top markets in a category → `async_get_category_markets` orders by `volume24hr` desc within the chosen tag, top N (Task 3). ✓
- Selection by category/tag → category dropdown + custom slug, tag-id resolution (Tasks 1, 3, 6). ✓
- Read-only → `switch.py` deleted (Task 0), platforms are `SENSOR` + `BINARY_SENSOR` only (Task 11). ✓
- "Maximum information" → every market exposes ~17 attributes; portfolio exposes per-position detail. ✓

**Placeholder scan:** no TBD/TODO; every code step contains complete code; every command lists expected output. The only forward-reference (Task 8 referencing Task 9 classes) is called out explicitly in a NOTE with the reason (review granularity), and both land before the HA load in Task 12.

**Type consistency:**
- `MarketInfo` fields (`market_id`, `yes_price`, `yes_token_id`, `midpoint`, `volume_24hr`, `liquidity`, `event_slug`) defined in Task 2 are used identically in coordinator (Task 5), entity (Task 7), and sensors (Tasks 8–10). ✓
- `Portfolio` (`value`, `position_count`, `total_cash_pnl`, `largest_position`) and `Position` (`title`, `outcome`, `size`, `avg_price`, `cur_price`, `current_value`, `cash_pnl`, `percent_pnl`, `slug`, `end_date`) defined in Task 2 are used identically in Task 3 and Task 9. ✓
- `PolymarketCoordinatorData(markets, portfolio)` (Task 4) is what the coordinator returns (Task 5) and what platforms read via `coordinator.data` (Tasks 8–10). ✓
- API method names `async_get_category_markets`, `async_get_midpoint`, `async_get_portfolio`, `async_resolve_tag_id` consistent across Tasks 3, 5, 6. ✓
- CONF keys (`CONF_CATEGORY`, `CONF_TOP_N`, `CONF_WALLET_ADDRESS`, `CONF_SCAN_INTERVAL`) defined in Task 1, used consistently in Tasks 5, 6, 11. ✓
