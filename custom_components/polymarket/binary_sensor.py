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
