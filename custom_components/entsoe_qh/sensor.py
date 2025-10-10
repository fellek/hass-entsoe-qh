from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CURRENT,
    ATTR_CURRENCY,
    ATTR_IN_DOMAIN,
    ATTR_OUT_DOMAIN,
    ATTR_SERIES,
    ATTR_SOURCE,
    ATTR_START,
    ATTR_STEP_MINUTES,
    ATTR_TODAY,
    ATTR_TODAY_AVG,
    ATTR_TODAY_MAX,
    ATTR_TODAY_MIN,
    ATTR_TOMORROW,
    ATTR_TOMORROW_AVG,
    ATTR_TOMORROW_MAX,
    ATTR_TOMORROW_MIN,
    ATTR_UNIT,
    ATTR_UPDATED_AT,
    DOMAIN,
)
from .coordinator import EntsoeCoordinator


@dataclass
class EntsoeSensorDescription:
    key: str
    translation_key: str
    series_key: str
    object_id_suffix: str


SENSOR_DESCRIPTIONS = (
    EntsoeSensorDescription(
        key="quarter_hour",
        translation_key="quarter_hour_price",
        series_key="quarter_hour",
        object_id_suffix="m15",
    ),
    EntsoeSensorDescription(
        key="hour",
        translation_key="hour_price",
        series_key="hour",
        object_id_suffix="h1",
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
        self._attr_suggested_object_id = (
            f"entso_e_energy_prices_{description.object_id_suffix}"
        )
        self._attr_native_value: float | None = None
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._attr_native_unit_of_measurement: Optional[str] = None
        self._last_payload: tuple[
            float | None,
            dict[str, Any],
            Optional[str],
        ] | None = None
        self._stored_unit: Optional[str] = None

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
        state, attributes, unit = self._calculate_state_payload()
        if unit is None and self._stored_unit is not None:
            unit = self._stored_unit
        if unit is not None:
            self._stored_unit = unit
            if attributes.get("unit_of_measurement") is None:
                attributes["unit_of_measurement"] = unit
        payload = (state, attributes, unit)
        if self._last_payload == payload:
            return
        self._last_payload = payload
        self._attr_native_value = state
        self._attr_extra_state_attributes = attributes
        self._attr_native_unit_of_measurement = unit
        super()._handle_coordinator_update()

    def _calculate_state_payload(
        self,
    ) -> tuple[float | None, dict[str, Any], Optional[str]]:
        data = self.coordinator.data or {}
        series = (data.get(ATTR_SERIES) or {}).get(self.description.series_key)
        if not series:
            return None, {}, data.get(ATTR_UNIT)

        state_value = series.get(ATTR_CURRENT)
        if state_value is None:
            state_value = self._fallback_state_value(series)
        state = float(state_value) if state_value is not None else None
        attributes = self._create_attributes(data, series)
        unit = data.get(ATTR_UNIT)
        return state, attributes, unit

    @staticmethod
    def _create_attributes(
        base_data: dict[str, Any],
        series_data: dict[str, Any],
    ) -> dict[str, Any]:
        attributes: dict[str, Any] = {}

        unit = base_data.get(ATTR_UNIT)
        if unit is not None:
            attributes["unit_of_measurement"] = unit

        currency = base_data.get(ATTR_CURRENCY)
        if currency is not None:
            attributes[ATTR_CURRENCY] = currency

        attributes[ATTR_STEP_MINUTES] = series_data.get(ATTR_STEP_MINUTES)
        attributes[ATTR_START] = series_data.get(ATTR_START)
        attributes[ATTR_TODAY] = list(series_data.get(ATTR_TODAY, []))

        for key in (ATTR_TODAY_MIN, ATTR_TODAY_MAX, ATTR_TODAY_AVG):
            value = series_data.get(key)
            if value is not None:
                attributes[key] = value

        if ATTR_TOMORROW in series_data:
            attributes[ATTR_TOMORROW] = list(series_data.get(ATTR_TOMORROW, []))
            for key in (ATTR_TOMORROW_MIN, ATTR_TOMORROW_MAX, ATTR_TOMORROW_AVG):
                value = series_data.get(key)
                if value is not None:
                    attributes[key] = value

        for key in (ATTR_UPDATED_AT, ATTR_SOURCE, ATTR_IN_DOMAIN, ATTR_OUT_DOMAIN):
            value = base_data.get(key)
            if value is not None:
                attributes[key] = value

        return attributes

    @staticmethod
    def _fallback_state_value(series_data: dict[str, Any]) -> float | None:
        today_values = series_data.get(ATTR_TODAY) or []
        for value in reversed(today_values):
            if value is not None:
                return float(value)

        tomorrow_values = series_data.get(ATTR_TOMORROW) or []
        for value in tomorrow_values:
            if value is not None:
                return float(value)

        return None
