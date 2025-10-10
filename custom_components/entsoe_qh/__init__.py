from __future__ import annotations

from datetime import timedelta
from typing import Any
import logging

try:  # pragma: no cover - import opcjonalny dla środowiska Home Assistant
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
except ModuleNotFoundError:  # pragma: no cover - środowisko testowe bez Home Assistant
    ConfigEntry = Any  # type: ignore[misc, assignment]
    HomeAssistant = Any  # type: ignore[misc, assignment]

    def async_get_clientsession(hass: Any) -> Any:  # type: ignore[unused-argument]
        raise ModuleNotFoundError(
            "Moduł homeassistant.helpers.aiohttp_client jest dostępny jedynie w Home Assistant."
        )

try:  # pragma: no cover - import wymagany w runtime Home Assistant
    from .coordinator import EntsoeCoordinator
except ModuleNotFoundError:  # pragma: no cover - środowisko testowe bez aiohttp
    class EntsoeCoordinator:  # type: ignore[too-many-function-args]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ModuleNotFoundError(
                "Klasa EntsoeCoordinator wymaga zależności dostępnych w Home Assistant."
            )

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
    PLATFORMS,
)
_LOGGER = logging.getLogger(__name__)


def _sanitize_entry_data(data: dict[str, Any]) -> dict[str, Any]:
    domain = (
        data.get(CONF_DOMAIN)
        or data.get("out_domain")
        or data.get("in_domain")
        or DEFAULT_DOMAIN
    )

    sanitized = {
        **data,
        CONF_DOMAIN: domain,
    }
    sanitized.pop("in_domain", None)
    sanitized.pop("out_domain", None)
    sanitized.pop("use_separate_domains", None)
    sanitized.setdefault(CONF_CURRENCY, DEFAULT_CURRENCY)
    sanitized.setdefault(CONF_ENERGY_UNIT, DEFAULT_ENERGY_UNIT)
    sanitized.setdefault(CONF_VAT, 0.0)
    sanitized.setdefault(CONF_CURRENCY_RATE, 1.0)
    return sanitized


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    new_data = _sanitize_entry_data(dict(config_entry.data))
    new_unique_id = new_data.get(CONF_DOMAIN, DEFAULT_DOMAIN)

    update_kwargs: dict[str, Any] = {}

    if new_data != config_entry.data:
        update_kwargs["data"] = new_data

    if config_entry.version != 2:
        update_kwargs["version"] = 2

    if config_entry.unique_id != new_unique_id:
        update_kwargs["unique_id"] = new_unique_id

    if update_kwargs:
        hass.config_entries.async_update_entry(config_entry, **update_kwargs)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    entry_data = _sanitize_entry_data(dict(entry.data))
    if entry_data != entry.data:
        hass.config_entries.async_update_entry(entry, data=entry_data, version=2)
    else:
        entry_data = {**entry_data}

    domain = entry_data[CONF_DOMAIN]

    coordinator = EntsoeCoordinator(
        hass=hass,
        session=session,
        security_token=entry_data[CONF_SECURITY_TOKEN],
        domain=domain,
        currency=entry_data[CONF_CURRENCY],
        energy_unit=entry_data[CONF_ENERGY_UNIT],
        vat=entry_data[CONF_VAT],
        currency_rate=entry_data.get(CONF_CURRENCY_RATE, 1.0),
        update_interval=timedelta(minutes=30),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
