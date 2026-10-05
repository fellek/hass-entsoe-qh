from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CURRENCY,
    CONF_CURRENCY_RATE,
    CONF_DOMAIN,
    CONF_ENERGY_UNIT,
    CONF_SECURITY_TOKEN,
    CONF_VAT,
    DEFAULT_CURRENCY,
    DEFAULT_DOMAIN,
    DEFAULT_ENERGY_UNIT,
    DOMAIN,
    ENTSOE_DOMAIN_CHOICES,
    SUPPORTED_CURRENCIES,
    SUPPORTED_ENERGY_UNITS,
)


DOMAIN_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            selector.SelectOptionDict(value=code, label=f"{country} ({code})")
            for country, code in ENTSOE_DOMAIN_CHOICES
        ],
        mode=selector.SelectSelectorMode.DROPDOWN,
        custom_value=False,
    )
)


def _sanitize_entry_data(data: dict[str, Any]) -> dict[str, Any]:
    domain = data.get(CONF_DOMAIN) or data.get("out_domain") or data.get("in_domain")
    if domain is None:
        domain = DEFAULT_DOMAIN

    token = data.get(CONF_SECURITY_TOKEN, "")
    if isinstance(token, str):
        token = token.strip()

    sanitized: dict[str, Any] = {
        CONF_SECURITY_TOKEN: token,
        CONF_DOMAIN: domain,
        CONF_CURRENCY: data.get(CONF_CURRENCY, DEFAULT_CURRENCY),
        CONF_ENERGY_UNIT: data.get(CONF_ENERGY_UNIT, DEFAULT_ENERGY_UNIT),
        CONF_VAT: data.get(CONF_VAT, 0.0),
        CONF_CURRENCY_RATE: data.get(CONF_CURRENCY_RATE, 1.0),
    }
    return sanitized


class EntsoeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        submitted = user_input or {}

        if user_input is not None:
            security_token = user_input.get(CONF_SECURITY_TOKEN)
            if security_token is None or security_token.strip() == "":
                errors[CONF_SECURITY_TOKEN] = "required"
            else:
                user_input[CONF_SECURITY_TOKEN] = security_token.strip()

            currency = user_input[CONF_CURRENCY]
            currency_rate = user_input.get(CONF_CURRENCY_RATE)
            if currency != "EUR" and (currency_rate is None or currency_rate <= 0):
                errors[CONF_CURRENCY_RATE] = "required"

            if not user_input.get(CONF_DOMAIN):
                errors[CONF_DOMAIN] = "required"

            if not errors:
                normalized = _sanitize_entry_data(user_input)
                domain = normalized[CONF_DOMAIN]
                await self.async_set_unique_id(domain)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="ENTSO-E", data=normalized)

        security_token_default = submitted.get(CONF_SECURITY_TOKEN, "")
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SECURITY_TOKEN, default=security_token_default): str,
                vol.Required(
                    CONF_DOMAIN,
                    default=submitted.get(CONF_DOMAIN, DEFAULT_DOMAIN),
                ): DOMAIN_SELECTOR,
                vol.Required(
                    CONF_CURRENCY,
                    default=submitted.get(CONF_CURRENCY, DEFAULT_CURRENCY),
                ): vol.In(SUPPORTED_CURRENCIES),
                vol.Required(
                    CONF_ENERGY_UNIT,
                    default=submitted.get(CONF_ENERGY_UNIT, DEFAULT_ENERGY_UNIT),
                ): vol.In(SUPPORTED_ENERGY_UNITS),
                vol.Optional(
                    CONF_CURRENCY_RATE,
                    default=submitted.get(CONF_CURRENCY_RATE, 1.0),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_VAT,
                    default=submitted.get(CONF_VAT, 0.0),
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EntsoeOptionsFlow()


class EntsoeOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        defaults = user_input or {**self.config_entry.data}

        if user_input is not None:
            currency = user_input[CONF_CURRENCY]
            currency_rate = user_input.get(CONF_CURRENCY_RATE)
            if currency != "EUR" and (currency_rate is None or currency_rate <= 0):
                errors[CONF_CURRENCY_RATE] = "required"

            if not user_input.get(CONF_DOMAIN):
                errors[CONF_DOMAIN] = "required"

            if not errors:
                normalized = _sanitize_entry_data({**self.config_entry.data, **user_input})
                return self.async_create_entry(title="", data=normalized)

        entry_data = _sanitize_entry_data({**self.config_entry.data, **defaults})

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SECURITY_TOKEN,
                    default=entry_data[CONF_SECURITY_TOKEN],
                ): str,
                vol.Required(
                    CONF_DOMAIN,
                    default=entry_data.get(CONF_DOMAIN, DEFAULT_DOMAIN),
                ): DOMAIN_SELECTOR,
                vol.Required(
                    CONF_CURRENCY,
                    default=entry_data.get(CONF_CURRENCY, DEFAULT_CURRENCY),
                ): vol.In(SUPPORTED_CURRENCIES),
                vol.Required(
                    CONF_ENERGY_UNIT,
                    default=entry_data.get(CONF_ENERGY_UNIT, DEFAULT_ENERGY_UNIT),
                ): vol.In(SUPPORTED_ENERGY_UNITS),
                vol.Optional(
                    CONF_CURRENCY_RATE,
                    default=entry_data.get(CONF_CURRENCY_RATE, 1.0),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_VAT,
                    default=entry_data.get(CONF_VAT, 0.0),
                ): vol.Coerce(float),
            }
        )

        return self.async_show_form(
            step_id="options",
            data_schema=options_schema,
            errors=errors,
        )

    async def async_create_entry(self, title: str, data: dict[str, Any]):
        new_data = _sanitize_entry_data({**self.config_entry.data, **data})
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return super().async_create_entry(title=title, data={})
