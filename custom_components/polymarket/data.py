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
