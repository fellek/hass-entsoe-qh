import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterable

import pytest

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "custom_components"))
sys.path.insert(0, str(project_root / "custom_components" / "entsoe_qh"))

ha_module = ModuleType("homeassistant")
sys.modules.setdefault("homeassistant", ha_module)

aiohttp_module = ModuleType("aiohttp")


class ClientSession:  # pragma: no cover - stub
    pass


class ClientError(Exception):  # pragma: no cover - stub
    pass


aiohttp_module.ClientSession = ClientSession
aiohttp_module.ClientError = ClientError
sys.modules.setdefault("aiohttp", aiohttp_module)

components_module = ModuleType("homeassistant.components")
sys.modules.setdefault("homeassistant.components", components_module)

sensor_module = ModuleType("homeassistant.components.sensor")


class SensorDeviceClass:
    MONETARY = "monetary"


class SensorStateClass:
    MEASUREMENT = "measurement"


class SensorEntity:
    def __init__(self) -> None:
        self.hass = None

    def async_write_ha_state(self) -> None:  # pragma: no cover - stub
        return None


sensor_module.SensorDeviceClass = SensorDeviceClass
sensor_module.SensorEntity = SensorEntity
sensor_module.SensorStateClass = SensorStateClass
sys.modules.setdefault("homeassistant.components.sensor", sensor_module)

config_entries_module = ModuleType("homeassistant.config_entries")


class ConfigEntry:  # pragma: no cover - stub
    def __init__(self, entry_id: str) -> None:
        self.entry_id = entry_id


config_entries_module.ConfigEntry = ConfigEntry
sys.modules.setdefault("homeassistant.config_entries", config_entries_module)

core_module = ModuleType("homeassistant.core")


class HomeAssistant:  # pragma: no cover - stub
    pass


core_module.HomeAssistant = HomeAssistant
sys.modules.setdefault("homeassistant.core", core_module)

entity_module = ModuleType("homeassistant.helpers.entity")


class DeviceInfo(dict):  # pragma: no cover - stub
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


entity_module.DeviceInfo = DeviceInfo
sys.modules.setdefault("homeassistant.helpers.entity", entity_module)

entity_platform_module = ModuleType("homeassistant.helpers.entity_platform")
AddEntitiesCallback = Callable[[Iterable], None]
entity_platform_module.AddEntitiesCallback = AddEntitiesCallback
sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform_module)

coordinator_module = ModuleType("homeassistant.helpers.update_coordinator")


class CoordinatorEntity:
    def __init__(self, coordinator) -> None:
        self.coordinator = coordinator
        if hasattr(coordinator, "async_add_listener"):
            coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self) -> None:  # pragma: no cover - stub
        if hasattr(self, "async_write_ha_state"):
            self.async_write_ha_state()

    def __class_getitem__(cls, item):  # pragma: no cover - stub
        return cls


coordinator_module.CoordinatorEntity = CoordinatorEntity
coordinator_module.UpdateFailed = type("UpdateFailed", (Exception,), {})


class DataUpdateCoordinator:
    def __init__(self, hass, logger, name=None, update_interval=None) -> None:  # pragma: no cover - stub
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    async def async_config_entry_first_refresh(self) -> None:  # pragma: no cover - stub
        return None

    def async_add_listener(self, update_callback):  # pragma: no cover - stub
        return lambda: None

    def __class_getitem__(cls, item):  # pragma: no cover - stub
        return cls


coordinator_module.DataUpdateCoordinator = DataUpdateCoordinator
sys.modules.setdefault("homeassistant.helpers.update_coordinator", coordinator_module)

aiohttp_client_module = ModuleType("homeassistant.helpers.aiohttp_client")


async def async_get_clientsession(hass):  # pragma: no cover - stub
    return None


aiohttp_client_module.async_get_clientsession = async_get_clientsession
sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client_module)

from entsoe_qh.sensor import (  # type: ignore  # noqa: E402
    EntsoePriceSensor,
    SENSOR_DESCRIPTIONS,
)
from entsoe_qh.shared.api import EntsoeApiClient, PricePoint  # type: ignore  # noqa: E402
from entsoe_qh.shared.constants import (  # type: ignore  # noqa: E402
    ATTR_SERIES,
    ATTR_TODAY,
    ATTR_TOMORROW,
)


class DummyCoordinator:
    def __init__(self) -> None:
        self.data = None
        self.last_update_success = True

    def async_add_listener(self, update_callback):
        return lambda: None

    def async_remove_listener(self, update_callback):
        return None


@pytest.fixture
def api_client() -> EntsoeApiClient:
    return EntsoeApiClient(
        session=None,
        security_token="token",
        domain="10YPL-AREA-----S",
        currency="EUR",
        energy_unit="kWh",
        vat=0.0,
        currency_rate=1.0,
    )


def _build_price_points(start: datetime, count: int, step_minutes: int) -> list[PricePoint]:
    points: list[PricePoint] = []
    for index in range(count):
        timestamp = start + timedelta(minutes=step_minutes * index)
        value = Decimal("40") + Decimal(index) / Decimal("10")
        points.append(
            PricePoint(
                timestamp=timestamp,
                price_eur_mwh=value,
                resolution_minutes=step_minutes,
            )
        )
    return points


def test_compact_attributes_generation(api_client: EntsoeApiClient) -> None:
    start = datetime(2025, 1, 5, tzinfo=timezone.utc)
    today_points = _build_price_points(start, 120, 15)
    data = api_client._convert_prices(today_points, start + timedelta(hours=10))

    series = data[ATTR_SERIES]["quarter_hour"]
    attributes = EntsoePriceSensor._create_attributes(data, series)

    assert len(series[ATTR_TODAY]) == 96
    assert ATTR_TOMORROW in series
    assert len(series[ATTR_TOMORROW]) == 24
    assert len(json.dumps(attributes)) < 8192

    forbidden_keys = {"raw", "series", "points", "time", "timestamp"}
    assert all(
        all(fragment not in key for fragment in forbidden_keys)
        for key in attributes
    )


def test_sensor_skips_duplicate_updates(api_client: EntsoeApiClient) -> None:
    coordinator = DummyCoordinator()
    entry = SimpleNamespace(entry_id="test-entry")
    sensor = EntsoePriceSensor(
        coordinator=coordinator,
        description=SENSOR_DESCRIPTIONS[0],
        entry=entry,
    )
    sensor.hass = SimpleNamespace()
    sensor.async_write_ha_state = lambda: setattr(sensor, "_state_writes", getattr(sensor, "_state_writes", 0) + 1)

    now = datetime(2025, 1, 5, 12, tzinfo=timezone.utc)
    points = _build_price_points(now.replace(hour=0), 96, 15)
    coordinator.data = api_client._convert_prices(points, now)

    sensor._handle_coordinator_update()
    first_count = getattr(sensor, "_state_writes", 0)
    sensor._handle_coordinator_update()
    second_count = getattr(sensor, "_state_writes", 0)

    assert first_count == 1
    assert second_count == 1


def test_sensor_uses_last_known_price_when_future_slot_missing(
    api_client: EntsoeApiClient,
) -> None:
    coordinator = DummyCoordinator()
    entry = SimpleNamespace(entry_id="test-entry")
    sensor = EntsoePriceSensor(
        coordinator=coordinator,
        description=SENSOR_DESCRIPTIONS[0],
        entry=entry,
    )
    sensor.hass = SimpleNamespace()
    sensor.async_write_ha_state = lambda: None

    now = datetime(2025, 1, 5, 23, 59, tzinfo=timezone.utc)
    points = _build_price_points(now.replace(hour=0, minute=0), 95, 15)
    coordinator.data = api_client._convert_prices(points, now)

    sensor._handle_coordinator_update()

    assert sensor.native_value is not None
    expected_value = float(points[-1].price_eur_mwh / Decimal("1000"))
    assert sensor.native_value == pytest.approx(expected_value, rel=1e-6)
    assert sensor._attr_suggested_object_id == "entso_e_energy_prices_m15"
