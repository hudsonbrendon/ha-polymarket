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
        self._attr_translation_key = "yes_odds"

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
        self._attr_translation_key = "volume_24h"

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
        self._attr_translation_key = "liquidity"

    @property
    def native_value(self) -> float | None:
        """Return liquidity."""
        return self._market.liquidity if self._market else None


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
        self._attr_translation_key = "portfolio_value"

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
        self._attr_translation_key = "portfolio_pnl"

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
        self._attr_translation_key = "portfolio_positions"

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
