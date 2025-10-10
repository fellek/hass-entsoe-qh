import asyncio

from custom_components.entsoe_qh import async_migrate_entry
from custom_components.entsoe_qh.const import CONF_DOMAIN, DEFAULT_DOMAIN

from tests.shouldly import should


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
    # // Arrange
    entry = DummyConfigEntry(
        data={CONF_DOMAIN: DEFAULT_DOMAIN},
        version=1,
        unique_id=f"{DEFAULT_DOMAIN}_{DEFAULT_DOMAIN}",
    )
    hass = DummyHass()

    # // Act
    result = asyncio.run(async_migrate_entry(hass, entry))

    # // Assert
    should(result).be(True)
    should(entry.unique_id).be(DEFAULT_DOMAIN)
    should(entry.version).be(2)
    should(entry.data[CONF_DOMAIN]).be(DEFAULT_DOMAIN)
    should(hass.config_entries.updates).not_be_empty()
