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


async def async_setup_entry(hass: HomeAssistant, entry: PolymarketConfigEntry) -> bool:
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


async def async_unload_entry(hass: HomeAssistant, entry: PolymarketConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: PolymarketConfigEntry) -> None:
    """Reload a config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
