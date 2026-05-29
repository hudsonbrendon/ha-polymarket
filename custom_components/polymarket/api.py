"""Async client for Polymarket's public Gamma, CLOB, and Data APIs."""

from __future__ import annotations

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
        # Widen the event pool so we can rank markets across events, not just
        # take whatever markets happen to live in the top_n events.
        event_limit = max(top_n, 20)
        events = await self._get(
            f"{GAMMA_BASE}/events",
            params={
                "limit": event_limit,
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
            markets.extend(
                parse_market(raw_market, event_title=event_title, event_slug=event_slug)
                for raw_market in event.get("markets", []) or []
            )
        markets.sort(key=lambda market: market.volume_24hr, reverse=True)
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
        value_payload = await self._get(f"{DATA_BASE}/value", params={"user": wallet})
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
            for raw in (
                positions_payload if isinstance(positions_payload, list) else []
            )
        ]
        return Portfolio(
            wallet=wallet,
            value=parse_portfolio_value(value_payload),
            positions=positions,
        )

    async def _get(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        """Perform a GET request and return parsed JSON."""
        try:
            async with (
                async_timeout.timeout(_TIMEOUT),
                self._session.request(method="get", url=url, params=params) as response,
            ):
                response.raise_for_status()
                return await response.json()
        except TimeoutError as exception:
            msg = f"Timeout fetching {url}"
            raise PolymarketApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching {url}: {exception}"
            raise PolymarketApiClientCommunicationError(msg) from exception
        except PolymarketApiClientError:
            raise
        except Exception as exception:
            msg = f"Unexpected error fetching {url}: {exception}"
            raise PolymarketApiClientError(msg) from exception
