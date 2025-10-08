from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CURRENCY,
    CONF_CURRENCY_RATE,
    CONF_ENERGY_UNIT,
    CONF_IN_DOMAIN,
    CONF_OUT_DOMAIN,
    CONF_SECURITY_TOKEN,
    CONF_VAT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EntsoeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    coordinator = EntsoeCoordinator(
        hass=hass,
        session=session,
        security_token=entry.data[CONF_SECURITY_TOKEN],
        in_domain=entry.data[CONF_IN_DOMAIN],
        out_domain=entry.data[CONF_OUT_DOMAIN],
        currency=entry.data[CONF_CURRENCY],
        energy_unit=entry.data[CONF_ENERGY_UNIT],
        vat=entry.data[CONF_VAT],
        currency_rate=entry.data.get(CONF_CURRENCY_RATE, 1.0),
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
