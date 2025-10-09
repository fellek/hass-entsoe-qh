from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DEFAULT_DOMAIN,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EntsoeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    entry_data = dict(entry.data)
    domain = entry_data.get(CONF_DOMAIN)
    in_domain = entry_data.get(CONF_IN_DOMAIN)
    out_domain = entry_data.get(CONF_OUT_DOMAIN)
    use_separate = entry_data.get(CONF_USE_SEPARATE_DOMAINS)

    if domain is None:
        if in_domain is not None and out_domain is not None and in_domain == out_domain:
            domain = in_domain
        elif out_domain is not None:
            domain = out_domain
        elif in_domain is not None:
            domain = in_domain
        else:
            domain = DEFAULT_DOMAIN

    if in_domain is None:
        in_domain = domain
    if out_domain is None:
        out_domain = domain
    if use_separate is None:
        use_separate = in_domain != out_domain

    updated_data = {**entry_data, CONF_DOMAIN: domain, CONF_USE_SEPARATE_DOMAINS: use_separate}
    if use_separate:
        updated_data[CONF_IN_DOMAIN] = in_domain
        updated_data[CONF_OUT_DOMAIN] = out_domain
    else:
        updated_data.pop(CONF_IN_DOMAIN, None)
        updated_data.pop(CONF_OUT_DOMAIN, None)

    if updated_data != entry.data:
        hass.config_entries.async_update_entry(entry, data=updated_data)
        entry_data = updated_data
    else:
        entry_data = {**entry_data}

    if entry_data.get(CONF_USE_SEPARATE_DOMAINS):
        coordinator_in_domain = entry_data.get(CONF_IN_DOMAIN, domain)
        coordinator_out_domain = entry_data.get(CONF_OUT_DOMAIN, domain)
    else:
        coordinator_in_domain = domain
        coordinator_out_domain = domain

    coordinator = EntsoeCoordinator(
        hass=hass,
        session=session,
        security_token=entry_data[CONF_SECURITY_TOKEN],
        in_domain=coordinator_in_domain,
        out_domain=coordinator_out_domain,
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
