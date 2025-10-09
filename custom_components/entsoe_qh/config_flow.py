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
    CONF_IN_DOMAIN,
    CONF_OUT_DOMAIN,
    CONF_USE_SEPARATE_DOMAINS,
    CONF_SECURITY_TOKEN,
    CONF_VAT,
    DEFAULT_CURRENCY,
    DEFAULT_DOMAIN,
    DEFAULT_USE_SEPARATE_DOMAINS,
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


def _resolve_domain(data: dict[str, Any]) -> str:
    domain = data.get(CONF_DOMAIN)
    if domain is not None:
        return domain
    if data.get(CONF_USE_SEPARATE_DOMAINS):
        out_domain = data.get(CONF_OUT_DOMAIN)
        if out_domain is not None:
            return out_domain
        in_domain = data.get(CONF_IN_DOMAIN)
        if in_domain is not None:
            return in_domain
    else:
        in_domain = data.get(CONF_IN_DOMAIN)
        out_domain = data.get(CONF_OUT_DOMAIN)
        if in_domain is not None and in_domain == out_domain:
            return in_domain
        if out_domain is not None:
            return out_domain
        if in_domain is not None:
            return in_domain
    return DEFAULT_DOMAIN


def _resolve_in_domain(data: dict[str, Any], fallback: str) -> str:
    domain = data.get(CONF_IN_DOMAIN)
    if domain is not None:
        return domain
    return fallback


def _resolve_out_domain(data: dict[str, Any], fallback: str) -> str:
    domain = data.get(CONF_OUT_DOMAIN)
    if domain is not None:
        return domain
    return fallback


def _normalize_domain_settings(data: dict[str, Any]) -> dict[str, Any]:
    normalized = {**data}
    use_separate = normalized.get(CONF_USE_SEPARATE_DOMAINS, DEFAULT_USE_SEPARATE_DOMAINS)
    normalized[CONF_USE_SEPARATE_DOMAINS] = use_separate
    if use_separate:
        out_domain = normalized.get(CONF_OUT_DOMAIN)
        if out_domain is None:
            out_domain = _resolve_out_domain(normalized, _resolve_domain(normalized))
        normalized[CONF_OUT_DOMAIN] = out_domain
        normalized[CONF_IN_DOMAIN] = normalized.get(
            CONF_IN_DOMAIN, _resolve_in_domain(normalized, out_domain)
        )
        normalized[CONF_DOMAIN] = out_domain
    else:
        normalized.pop(CONF_IN_DOMAIN, None)
        normalized.pop(CONF_OUT_DOMAIN, None)
    return normalized


def _build_domain_schema(
    *,
    defaults: dict[str, Any],
    use_separate: bool,
) -> dict[Any, Any]:
    schema: dict[Any, Any] = {
        vol.Required(
            CONF_USE_SEPARATE_DOMAINS,
            default=defaults.get(CONF_USE_SEPARATE_DOMAINS, use_separate),
        ): bool,
    }
    if use_separate:
        schema[vol.Required(
            CONF_IN_DOMAIN,
            default=_resolve_in_domain(defaults, _resolve_domain(defaults)),
        )] = DOMAIN_SELECTOR
        schema[vol.Required(
            CONF_OUT_DOMAIN,
            default=_resolve_out_domain(defaults, _resolve_domain(defaults)),
        )] = DOMAIN_SELECTOR
    else:
        schema[vol.Required(
            CONF_DOMAIN,
            default=_resolve_domain(defaults),
        )] = DOMAIN_SELECTOR
    return schema


class EntsoeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        submitted = user_input or {}
        use_separate = submitted.get(
            CONF_USE_SEPARATE_DOMAINS, DEFAULT_USE_SEPARATE_DOMAINS
        )

        if user_input is not None:
            currency = user_input[CONF_CURRENCY]
            currency_rate = user_input.get(CONF_CURRENCY_RATE)
            if currency != "EUR" and (currency_rate is None or currency_rate <= 0):
                errors[CONF_CURRENCY_RATE] = "required"

            if use_separate:
                if not user_input.get(CONF_IN_DOMAIN):
                    errors[CONF_IN_DOMAIN] = "required"
                if not user_input.get(CONF_OUT_DOMAIN):
                    errors[CONF_OUT_DOMAIN] = "required"
            else:
                if not user_input.get(CONF_DOMAIN):
                    errors[CONF_DOMAIN] = "required"

            if not errors:
                normalized = _normalize_domain_settings(user_input)
                if normalized.get(CONF_USE_SEPARATE_DOMAINS):
                    in_domain = user_input[CONF_IN_DOMAIN]
                    out_domain = user_input[CONF_OUT_DOMAIN]
                    unique_id = f"{in_domain}_{out_domain}"
                else:
                    domain = normalized[CONF_DOMAIN]
                    unique_id = f"{domain}_{domain}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="ENTSO-E", data=normalized)

        security_token_default = submitted.get(CONF_SECURITY_TOKEN)
        schema_fields: dict[Any, Any]
        if security_token_default is None:
            schema_fields = {vol.Required(CONF_SECURITY_TOKEN): str}
        else:
            schema_fields = {
                vol.Required(CONF_SECURITY_TOKEN, default=security_token_default): str
            }

        schema_fields.update(
            _build_domain_schema(defaults=submitted, use_separate=use_separate)
        )
        schema_fields.update(
            {
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

        data_schema = vol.Schema(schema_fields)
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
        defaults = user_input or {**self.config_entry.data}
        use_separate = defaults.get(
            CONF_USE_SEPARATE_DOMAINS,
            self.config_entry.data.get(CONF_USE_SEPARATE_DOMAINS, DEFAULT_USE_SEPARATE_DOMAINS),
        )

        if user_input is not None:
            currency = user_input[CONF_CURRENCY]
            currency_rate = user_input.get(CONF_CURRENCY_RATE)
            if currency != "EUR" and (currency_rate is None or currency_rate <= 0):
                errors[CONF_CURRENCY_RATE] = "required"

            if use_separate:
                if not user_input.get(CONF_IN_DOMAIN):
                    errors[CONF_IN_DOMAIN] = "required"
                if not user_input.get(CONF_OUT_DOMAIN):
                    errors[CONF_OUT_DOMAIN] = "required"
            else:
                if not user_input.get(CONF_DOMAIN):
                    errors[CONF_DOMAIN] = "required"

            if not errors:
                normalized = _normalize_domain_settings({**self.config_entry.data, **user_input})
                return self.async_create_entry(title="", data=normalized)

        entry_data = {**self.config_entry.data, **defaults}

        schema_fields: dict[Any, Any] = {
            vol.Required(
                CONF_SECURITY_TOKEN,
                default=entry_data[CONF_SECURITY_TOKEN],
            ): str
        }

        schema_fields.update(
            _build_domain_schema(defaults=entry_data, use_separate=use_separate)
        )

        schema_fields.update(
            {
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

        options_schema = vol.Schema(schema_fields)
        return self.async_show_form(
            step_id="options",
            data_schema=options_schema,
            errors=errors,
        )

    async def async_create_entry(self, title: str, data: dict[str, Any]):
        new_data = _normalize_domain_settings({**self.config_entry.data, **data})
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return super().async_create_entry(title=title, data={})
