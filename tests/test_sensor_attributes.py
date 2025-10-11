from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.entsoe_qh.shared.attributes import (
    MAX_SERIES_POINTS,
    compact_series_attributes,
)
from custom_components.entsoe_qh.shared.constants import (
    ATTR_DURATION_MINUTES,
    ATTR_PRICE_ID,
    ATTR_PRICE_START,
    ATTR_RAW_PRICE,
    ATTR_SERIES_TOTAL_POINTS,
    ATTR_SERIES_TRUNCATED,
    ATTR_VALUE,
)
from assertpy import assert_that


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def test_compact_series_attributes_limits_payload_size():
    # Arrange
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    values = [float(index) for index in range(MAX_SERIES_POINTS + 5)]
    series = {
        ATTR_DURATION_MINUTES: 15,
        ATTR_PRICE_ID: [f"pt15m-{index}" for index in range(len(values))],
        ATTR_PRICE_START: [
            _iso(base_time + timedelta(minutes=15 * index))
            for index in range(len(values))
        ],
        ATTR_VALUE: values,
        ATTR_RAW_PRICE: [value * 10 for value in values],
    }

    # Act
    compacted = compact_series_attributes(series)

    # Assert
    assert_that(compacted[ATTR_SERIES_TOTAL_POINTS]).is_equal_to(len(values))
    assert_that(compacted[ATTR_PRICE_ID]).is_length(MAX_SERIES_POINTS)
    assert_that(compacted[ATTR_VALUE]).is_length(MAX_SERIES_POINTS)
    assert_that(compacted[ATTR_RAW_PRICE]).is_length(MAX_SERIES_POINTS)
    assert_that(compacted[ATTR_PRICE_START]).is_length(MAX_SERIES_POINTS)
    assert_that(compacted[ATTR_SERIES_TRUNCATED]).is_true()
    assert_that(all(item.endswith("Z") for item in compacted[ATTR_PRICE_START])).is_true()


def test_compact_series_attributes_handles_empty_values():
    # Arrange
    series = {ATTR_DURATION_MINUTES: 60}

    # Act
    compacted = compact_series_attributes(series)

    # Assert
    assert_that(compacted[ATTR_DURATION_MINUTES]).is_equal_to(60)
    assert_that(compacted[ATTR_SERIES_TOTAL_POINTS]).is_equal_to(0)


def test_sensor_uses_measurement_state_class():
    # Arrange
    sensor_module = pytest.importorskip("homeassistant.components.sensor")
    entsoe_sensor_module = pytest.importorskip("custom_components.entsoe_qh.sensor")
    # Act
    # Assert
    assert_that(entsoe_sensor_module.EntsoePriceSensor._attr_state_class).is_equal_to(
        sensor_module.SensorStateClass.MEASUREMENT
    )


def test_sensor_uses_generic_device_class_for_prices():
    # Arrange
    entsoe_sensor_module = pytest.importorskip("custom_components.entsoe_qh.sensor")

    # Act
    # Assert
    assert_that(entsoe_sensor_module.EntsoePriceSensor._attr_device_class).is_equal_to(
        None
    )


def test_sensor_descriptions_define_display_and_object_id_parts():
    # Arrange
    entsoe_sensor_module = pytest.importorskip("custom_components.entsoe_qh.sensor")
    expected_labels = {
        "quarter_hour": ("15 min", "15min"),
        "half_hour": ("30 min", "30min"),
        "hour": ("1 h", "1h"),
    }

    # Act
    descriptions = entsoe_sensor_module.SENSOR_DESCRIPTIONS

    # Assert
    for key, (label, suffix) in expected_labels.items():
        description = descriptions[key]
        assert_that(description.period_label).is_equal_to(label)
        assert_that(description.translation_placeholders["period"]).is_equal_to(label)
        assert_that(description.object_id_suffix).is_equal_to(suffix)
        assert_that(description.entity_name).is_equal_to(
            f"ENTSO-E Energy Prices {label}"
        )
