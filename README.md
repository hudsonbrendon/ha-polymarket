<p align="center">
  <img src="custom_components/polymarket/brand/logo.png" alt="Polymarket" width="420">
</p>

# Polymarket for Home Assistant

[![Tests](https://github.com/hudsonbrendon/ha-polymarket/actions/workflows/test.yml/badge.svg)](https://github.com/hudsonbrendon/ha-polymarket/actions/workflows/test.yml)
[![Lint](https://github.com/hudsonbrendon/ha-polymarket/actions/workflows/lint.yml/badge.svg)](https://github.com/hudsonbrendon/ha-polymarket/actions/workflows/lint.yml)
[![Validate](https://github.com/hudsonbrendon/ha-polymarket/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/ha-polymarket/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/ha-polymarket)](https://github.com/hudsonbrendon/ha-polymarket/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **read-only** custom integration that surfaces [Polymarket](https://polymarket.com)
data in Home Assistant: live odds, volume and liquidity for the top markets in a
category you choose, plus an optional wallet portfolio (value, open positions and
unrealized P&L).

All data comes from Polymarket's public **Gamma**, **CLOB** and **Data** APIs.
No login, no private keys, no trading.

## Features

- 🎯 **Top markets by category** — pick a category (Politics, Sports, Crypto, …) or
  any Polymarket tag slug; the integration tracks the top markets by 24h volume.
- 📊 **Live odds** — a **YES odds (%)** sensor per market (prefers the CLOB
  midpoint), with full detail in attributes: outcomes, prices, best bid/ask, last
  trade, 24h change, volume, liquidity, end date and a link to the market.
- 💵 **Volume & liquidity** — **24h volume (USD)** and **Liquidity (USD)** sensors
  per market.
- ⚖️ **Resolution** — a **Resolved** binary sensor, on once a market has closed.
- 👛 **Optional portfolio** — add a public wallet address to also get **Value (USD)**,
  **Unrealized P&L (USD)** and **Open positions** (count + per-position detail).
- ⏱️ **Configurable update interval** — tune polling (5–360 minutes) and the number
  of tracked markets from the integration's options.
- 🌍 **Translations** — English, Spanish and Portuguese (PT and BR).

## Requirements

- Home Assistant **2025.2.4** or newer.
- Internet access to Polymarket's public APIs (no account or API key required).

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add the repository URL `https://github.com/hudsonbrendon/ha-polymarket` and
   choose the **Integration** category.
3. Search for **Polymarket** in HACS, install it, and **restart Home Assistant**.

### Manual

1. Copy `custom_components/polymarket/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration → Polymarket**.
2. Choose a **Category**, set how many top markets to track, and (optionally) paste
   a **wallet address** (`0x…`) to also track its portfolio.
3. Submit — one device per market is created, plus a Portfolio device if a wallet
   was given.

The number of tracked markets and the update interval can be changed later from the
integration's **Configure** (options) dialog.

## Entities

| Type | Entity | Notes |
|---|---|---|
| `sensor` | YES odds | per market — probability %, full market detail in attributes |
| `sensor` | 24h volume, Liquidity | per market — USD |
| `binary_sensor` | Resolved | per market — on once the market has closed |
| `sensor` | Value, Unrealized P&L, Open positions | portfolio (only if a wallet is configured); positions list in attributes |

## How it works

A single Home Assistant `DataUpdateCoordinator` polls three public Polymarket APIs
each interval: **Gamma** (`gamma-api.polymarket.com`) for the category's events and
markets, **CLOB** (`clob.polymarket.com`) for a live midpoint per market's YES
token, and the **Data** API (`data-api.polymarket.com`) for the optional wallet's
value and positions. Markets across the category's events are ranked by 24h volume
and the top N are exposed. A failing wallet lookup degrades gracefully — market data
stays available.

## Limitations

- **Read-only.** The integration never places orders and never handles private keys.
- Polymarket's public APIs are unauthenticated and rate-limited; very short update
  intervals with a large market count may be throttled.
- The wallet portfolio uses Polymarket's Data API, which reflects on-chain positions
  for the given **public** address only.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and pull requests are welcome.

## License

[MIT](LICENSE) © Hudson Brendon
