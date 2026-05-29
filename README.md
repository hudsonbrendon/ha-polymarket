# Polymarket for Home Assistant

A read-only custom integration that surfaces [Polymarket](https://polymarket.com) data in Home Assistant: live odds, volume, and liquidity for the top markets in a category you choose, plus an optional wallet portfolio (value, open positions, and unrealized P&L).

## What you get

Per config entry you choose a **category** (Politics, Sports, Crypto, …) and how many top markets to track. For each market you get:

- **YES odds (%)** — live probability (prefers the CLOB midpoint), with full detail in attributes (outcomes, prices, best bid/ask, last trade, 24h change, volume, liquidity, end date, link).
- **24h volume (USD)** and **Liquidity (USD)** sensors.
- **Resolved** binary sensor — on when the market has closed.

Add a wallet address (optional) to also get a **Portfolio** device:

- **Value (USD)**, **Unrealized P&L (USD)**, and **Open positions** (count + per-position detail in attributes).

All data comes from Polymarket's public Gamma, CLOB, and Data APIs. No login, no private keys, no trading.

## Installation

Install via [HACS](https://hacs.xyz) as a custom repository, or copy `custom_components/polymarket` into your Home Assistant `config/custom_components/` directory and restart. Then add the **Polymarket** integration from Settings → Devices & Services.

## Configuration

Configured entirely through the UI: pick a category, set how many markets to track, and optionally paste a wallet address (`0x…`). The update interval and market count can be changed later under the integration's **Configure** options.

## Development

```bash
scripts/setup    # install runtime deps
scripts/develop  # run Home Assistant with this integration loaded
scripts/lint     # ruff
python3 -m pytest tests/ -q  # unit tests (models + API client)
```
