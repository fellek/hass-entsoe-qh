from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_PRICES_TODAY,
    ATTR_PRICES_TOMORROW,
    ATTR_PRICE_FIELDS,
    ATTR_SERIES,
    ATTR_UPDATED_AT,
    DOMAIN,
)
from .coordinator import EntsoeCoordinator


@dataclass
class EntsoeSensorDescription:
    key: str
    translation_key: str
    series_key: str


SENSOR_DESCRIPTIONS = (
    EntsoeSensorDescription(
        key="quarter_hour",
        translation_key="quarter_hour_price",
        series_key="quarter_hour",
    ),
    EntsoeSensorDescription(
        key="hour",
        translation_key="hour_price",
        series_key="hour",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EntsoeCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        EntsoePriceSensor(coordinator=coordinator, description=description, entry=entry)
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class EntsoePriceSensor(CoordinatorEntity[EntsoeCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(
        self,
        coordinator: EntsoeCoordinator,
        description: EntsoeSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.description = description
        self._entry = entry
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None:
            return None
        series = (data.get(ATTR_SERIES) or {}).get(self.description.series_key, {})
        value = series.get("current")
        return None if value is None else float(value)

    @property
    def native_unit_of_measurement(self) -> str | None:
        data = self.coordinator.data
        if data is None:
            return None
        return data.get("unit")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        series = (data.get(ATTR_SERIES) or {}).get(self.description.series_key, {})
        attributes: dict[str, Any] = {
            ATTR_UPDATED_AT: data.get(ATTR_UPDATED_AT),
            ATTR_PRICE_FIELDS: data.get(ATTR_PRICE_FIELDS, []),
            ATTR_PRICES_TODAY: series.get(ATTR_PRICES_TODAY, []),
            ATTR_PRICES_TOMORROW: series.get(ATTR_PRICES_TOMORROW, []),
        }
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="ENTSO-E Energy Prices",
            manufacturer="ENTSO-E",
        )

    @property
    def should_poll(self) -> bool:
        return False
