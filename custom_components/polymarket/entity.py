"""Base entities for the Polymarket integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
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
