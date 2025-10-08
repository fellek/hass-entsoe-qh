from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_CURRENCY,
    CONF_CURRENCY_RATE,
    CONF_ENERGY_UNIT,
    CONF_IN_DOMAIN,
    CONF_OUT_DOMAIN,
    CONF_SECURITY_TOKEN,
    CONF_VAT,
    DEFAULT_CURRENCY,
    DEFAULT_ENERGY_UNIT,
    DEFAULT_IN_DOMAIN,
    DEFAULT_OUT_DOMAIN,
    DOMAIN,
    SUPPORTED_CURRENCIES,
    SUPPORTED_ENERGY_UNITS,
)


class EntsoeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            currency = user_input[CONF_CURRENCY]
            currency_rate = user_input.get(CONF_CURRENCY_RATE)
            if currency != "EUR" and (currency_rate is None or currency_rate <= 0):
                errors[CONF_CURRENCY_RATE] = "required"
            if not errors:
                unique_id = f"{user_input[CONF_IN_DOMAIN]}_{user_input[CONF_OUT_DOMAIN]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="ENTSO-E", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SECURITY_TOKEN): str,
                vol.Required(CONF_IN_DOMAIN, default=DEFAULT_IN_DOMAIN): str,
                vol.Required(CONF_OUT_DOMAIN, default=DEFAULT_OUT_DOMAIN): str,
                vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): vol.In(SUPPORTED_CURRENCIES),
                vol.Required(CONF_ENERGY_UNIT, default=DEFAULT_ENERGY_UNIT): vol.In(
                    SUPPORTED_ENERGY_UNITS
                ),
                vol.Optional(CONF_CURRENCY_RATE, default=1.0): vol.Coerce(float),
                vol.Optional(CONF_VAT, default=0.0): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @callback
    def async_get_options_flow(self, config_entry: config_entries.ConfigEntry):
        return EntsoeOptionsFlow(config_entry)


class EntsoeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            currency = user_input[CONF_CURRENCY]
            currency_rate = user_input.get(CONF_CURRENCY_RATE)
            if currency != "EUR" and (currency_rate is None or currency_rate <= 0):
                errors[CONF_CURRENCY_RATE] = "required"
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        entry_data = self.config_entry.data
        options_schema = vol.Schema(
            {
                vol.Required(CONF_SECURITY_TOKEN, default=entry_data[CONF_SECURITY_TOKEN]): str,
                vol.Required(CONF_IN_DOMAIN, default=entry_data.get(CONF_IN_DOMAIN, DEFAULT_IN_DOMAIN)): str,
                vol.Required(CONF_OUT_DOMAIN, default=entry_data.get(CONF_OUT_DOMAIN, DEFAULT_OUT_DOMAIN)): str,
                vol.Required(CONF_CURRENCY, default=entry_data.get(CONF_CURRENCY, DEFAULT_CURRENCY)): vol.In(
                    SUPPORTED_CURRENCIES
                ),
                vol.Required(
                    CONF_ENERGY_UNIT,
                    default=entry_data.get(CONF_ENERGY_UNIT, DEFAULT_ENERGY_UNIT),
                ): vol.In(SUPPORTED_ENERGY_UNITS),
                vol.Optional(
                    CONF_CURRENCY_RATE,
                    default=entry_data.get(CONF_CURRENCY_RATE, 1.0),
                ): vol.Coerce(float),
                vol.Optional(CONF_VAT, default=entry_data.get(CONF_VAT, 0.0)): vol.Coerce(float),
            }
        )
        return self.async_show_form(
            step_id="options",
            data_schema=options_schema,
            errors=errors,
        )

    async def async_create_entry(self, title: str, data: dict[str, Any]):
        new_data = {**self.config_entry.data, **data}
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return super().async_create_entry(title=title, data={})
