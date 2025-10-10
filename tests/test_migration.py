import asyncio
import pytest

from custom_components.entsoe_qh import async_migrate_entry, _sanitize_entry_data
from custom_components.entsoe_qh.const import (
    CONF_CURRENCY,
    CONF_CURRENCY_RATE,
    CONF_DOMAIN,
    CONF_ENERGY_UNIT,
    CONF_VAT,
    DEFAULT_CURRENCY,
    DEFAULT_DOMAIN,
    DEFAULT_ENERGY_UNIT,
)

from tests.assertions import assert_that


class DummyConfigEntry:
    def __init__(self, data: dict, version: int, unique_id: str | None):
        self.data = data
        self.version = version
        self.unique_id = unique_id
        self.entry_id = "dummy"


class DummyConfigEntryManager:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    def async_update_entry(self, entry: DummyConfigEntry, **kwargs):
        if "data" in kwargs:
            entry.data = kwargs["data"]
        if "version" in kwargs:
            entry.version = kwargs["version"]
        if "unique_id" in kwargs:
            entry.unique_id = kwargs["unique_id"]
        self.updates.append(kwargs)


class DummyHass:
    def __init__(self) -> None:
        self.config_entries = DummyConfigEntryManager()


def test_async_migrate_entry_updates_unique_id_and_version():
    # Arrange
    entry = DummyConfigEntry(
        data={CONF_DOMAIN: DEFAULT_DOMAIN},
        version=1,
        unique_id=f"{DEFAULT_DOMAIN}_{DEFAULT_DOMAIN}",
    )
    hass = DummyHass()

    # Act
    result = asyncio.run(async_migrate_entry(hass, entry))

    # Assert
    assert_that(result).is_true()
    assert_that(entry.unique_id).is_equal_to(DEFAULT_DOMAIN)
    assert_that(entry.version).is_equal_to(2)
    assert_that(entry.data[CONF_DOMAIN]).is_equal_to(DEFAULT_DOMAIN)
    assert_that(hass.config_entries.updates).is_not_empty()


def test_async_migrate_entry_without_changes_keeps_configuration():
    # Arrange
    entry = DummyConfigEntry(
        data={
            CONF_DOMAIN: DEFAULT_DOMAIN,
            CONF_CURRENCY: DEFAULT_CURRENCY,
            CONF_ENERGY_UNIT: DEFAULT_ENERGY_UNIT,
            CONF_VAT: 0.0,
            CONF_CURRENCY_RATE: 1.0,
        },
        version=2,
        unique_id=DEFAULT_DOMAIN,
    )
    hass = DummyHass()

    # Act
    result = asyncio.run(async_migrate_entry(hass, entry))

    # Assert
    assert_that(result).is_true()
    assert_that(entry.unique_id).is_equal_to(DEFAULT_DOMAIN)
    assert_that(entry.version).is_equal_to(2)
    assert_that(entry.data).is_equal_to(
        {
            CONF_DOMAIN: DEFAULT_DOMAIN,
            CONF_CURRENCY: DEFAULT_CURRENCY,
            CONF_ENERGY_UNIT: DEFAULT_ENERGY_UNIT,
            CONF_VAT: 0.0,
            CONF_CURRENCY_RATE: 1.0,
        }
    )
    assert_that(hass.config_entries.updates).is_empty()


def test_sanitize_entry_data_normalizes_domains_and_defaults():
    # Arrange
    raw_data = {
        "in_domain": DEFAULT_DOMAIN,
        "out_domain": DEFAULT_DOMAIN,
        CONF_DOMAIN: "",
        "use_separate_domains": True,
    }

    # Act
    sanitized = _sanitize_entry_data(raw_data)

    # Assert
    assert_that(sanitized).is_equal_to(
        {
            CONF_DOMAIN: DEFAULT_DOMAIN,
            CONF_CURRENCY: DEFAULT_CURRENCY,
            CONF_ENERGY_UNIT: DEFAULT_ENERGY_UNIT,
            CONF_VAT: 0.0,
            CONF_CURRENCY_RATE: 1.0,
        }
    )
