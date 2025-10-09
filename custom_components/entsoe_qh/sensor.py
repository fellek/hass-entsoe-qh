from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_PRICES_TODAY,
    ATTR_PRICES_TOMORROW,
    ATTR_PRICE_FIELDS,
    ATTR_UPDATED_AT,
    DOMAIN,
)
from .coordinator import EntsoeCoordinator


@dataclass
class EntsoeSensorDescription:
    key: str
    name: str
    attribute_key: str


SENSOR_DESCRIPTIONS = (
    EntsoeSensorDescription(
        key="quarter_hour",
        name="Cena energii 15 min",
        attribute_key="current_price",
    ),
    EntsoeSensorDescription(
        key="hour",
        name="Cena energii 1h",
        attribute_key="hour_price",
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
    _attr_state_class = SensorStateClass.MEASUREMENT

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
        self._attr_name = description.name

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None:
            return None
        value = data.get(self.description.attribute_key)
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
        attributes: dict[str, Any] = {
            ATTR_UPDATED_AT: data.get(ATTR_UPDATED_AT),
            ATTR_PRICE_FIELDS: data.get(ATTR_PRICE_FIELDS, []),
            "prices": data.get("prices", []),
            ATTR_PRICES_TODAY: data.get(ATTR_PRICES_TODAY, []),
            ATTR_PRICES_TOMORROW: data.get(ATTR_PRICES_TOMORROW, []),
        }
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="ENTSO-E Ceny energii",
            manufacturer="ENTSO-E",
        )

    @property
    def should_poll(self) -> bool:
        return False
