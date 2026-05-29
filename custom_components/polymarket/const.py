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
