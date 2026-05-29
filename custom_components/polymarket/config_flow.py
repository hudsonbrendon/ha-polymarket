"""Config and options flow for the Polymarket integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PolymarketApiClient, PolymarketApiClientError
from .const import (
    CATEGORIES,
    CONF_CATEGORY,
    CONF_SCAN_INTERVAL,
    CONF_TOP_N,
    CONF_WALLET_ADDRESS,
    DEFAULT_CATEGORY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOP_N,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MAX_TOP_N,
    MIN_SCAN_INTERVAL,
    MIN_TOP_N,
)

_WALLET_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def _category_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=slug, label=label)
                for slug, label in CATEGORIES.items()
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
            custom_value=True,
        )
    )


def _top_n_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_TOP_N, max=MAX_TOP_N, step=1, mode=selector.NumberSelectorMode.BOX
        )
    )


def _scan_interval_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL,
            max=MAX_SCAN_INTERVAL,
            step=1,
            unit_of_measurement="min",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


class PolymarketFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect category, top N, and an optional wallet address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            wallet = (user_input.get(CONF_WALLET_ADDRESS) or "").strip()
            category = user_input[CONF_CATEGORY].strip().lower()
            if wallet and not _WALLET_RE.match(wallet):
                errors[CONF_WALLET_ADDRESS] = "invalid_wallet"
            if not errors:
                try:
                    await self._validate(category, wallet or None)
                except PolymarketApiClientError as exception:
                    LOGGER.warning("Validation failed: %s", exception)
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(
                        f"{category}:{wallet.lower() or 'no-wallet'}"
                    )
                    self._abort_if_unique_id_configured()
                    title = CATEGORIES.get(category, category.title())
                    if wallet:
                        title = f"{title} + wallet"
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_CATEGORY: category,
                            CONF_TOP_N: int(user_input[CONF_TOP_N]),
                            CONF_WALLET_ADDRESS: wallet,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CATEGORY, default=DEFAULT_CATEGORY
                    ): _category_selector(),
                    vol.Required(CONF_TOP_N, default=DEFAULT_TOP_N): _top_n_selector(),
                    vol.Optional(
                        CONF_WALLET_ADDRESS, default=""
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
            errors=errors,
        )

    async def _validate(self, category: str, wallet: str | None) -> None:
        """Hit the APIs once to confirm the category (and wallet) work."""
        client = PolymarketApiClient(session=async_get_clientsession(self.hass))
        await client.async_get_category_markets(category, top_n=1)
        if wallet:
            await client.async_get_portfolio(wallet, top_n=1)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,  # noqa: ARG004
    ) -> PolymarketOptionsFlow:
        """Return the options flow."""
        return PolymarketOptionsFlow()


class PolymarketOptionsFlow(config_entries.OptionsFlow):
    """Allow editing top N and scan interval after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOP_N,
                        default=current.get(CONF_TOP_N, DEFAULT_TOP_N),
                    ): _top_n_selector(),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): _scan_interval_selector(),
                }
            ),
        )
