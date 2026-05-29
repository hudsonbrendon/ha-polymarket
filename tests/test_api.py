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
