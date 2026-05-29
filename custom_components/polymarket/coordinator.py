"""DataUpdateCoordinator for the Polymarket integration."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

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
