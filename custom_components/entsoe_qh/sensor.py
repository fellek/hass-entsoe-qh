from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EntsoeCoordinator
from .shared.models import SeriesData


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
        self._attr_translation_key = description.translation_key
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._last_published: tuple[float | None, dict[str, Any]] | None = None

    @property
    def native_value(self) -> float | None:
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._attr_native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attr_extra_state_attributes

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

    def _handle_coordinator_update(self) -> None:
        series = self._get_series_data()

        if series is None:
            if self._last_published is None or self._last_published[0] is not None or self._last_published[1]:
                self._attr_native_value = None
                self._attr_native_unit_of_measurement = None
                self._attr_extra_state_attributes = {}
                self._last_published = (None, {})
                super()._handle_coordinator_update()
            return

        self._attr_native_unit_of_measurement = series.unit
        attributes = series.as_attributes()
        comparison_state = series.current
        comparison_attributes = deepcopy(attributes)

        if self._last_published is not None:
            last_state, last_attributes = self._last_published
            if last_state == comparison_state and last_attributes == comparison_attributes:
                return

        self._attr_native_value = comparison_state
        self._attr_extra_state_attributes = attributes
        self._last_published = (comparison_state, comparison_attributes)
        super()._handle_coordinator_update()

    def _get_series_data(self) -> SeriesData | None:
        data = self.coordinator.data
        if data is None:
            return None
        return data.get(self.description.series_key)
