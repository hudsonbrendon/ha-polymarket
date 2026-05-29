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
