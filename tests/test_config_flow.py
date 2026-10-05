from __future__ import annotations

import sys
from types import ModuleType

from assertpy import assert_that


class DummyModule(ModuleType):
    """Simple module that allows attribute updates through init."""

    def __init__(self, name: str, **attributes):
        super().__init__(name)
        for key, value in attributes.items():
            setattr(self, key, value)


if "voluptuous" not in sys.modules:
    def _coerce(_type):
        def _converter(value):
            return value

        return _converter

    class _Schema:
        def __init__(self, schema):
            self.schema = schema

    vol_module = DummyModule(
        "voluptuous",
        Schema=_Schema,
        Required=lambda key, default=None: key,
        Optional=lambda key, default=None: key,
        Coerce=_coerce,
        In=lambda choices: choices,
    )
    sys.modules["voluptuous"] = vol_module


if "homeassistant" not in sys.modules:
    ha_module = DummyModule("homeassistant")
    ha_module.__path__ = []  # type: ignore[attr-defined]

    class ConfigEntry:  # type: ignore[too-few-public-methods]
        def __init__(self) -> None:
            self.data: dict[str, object] = {}

    class ConfigFlow:  # type: ignore[too-few-public-methods]
        VERSION = 1

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        async def async_set_unique_id(self, _unique_id: str) -> None:
            return None

        def _abort_if_unique_id_configured(self) -> None:
            return None

        def async_create_entry(self, title: str, data: dict[str, object]):
            return {"title": title, "data": data}

        def async_show_form(self, **kwargs):
            return kwargs

    class OptionsFlow:  # type: ignore[too-few-public-methods]
        # Mirrors Home Assistant 2025.12: the flow manager sets hass and handler
        # after construction, and config_entry is a read-only property.
        hass = None
        handler: str | None = None

        @property
        def config_entry(self):
            if self.hass is None or self.handler is None:
                raise ValueError("The config entry is not available during initialisation")
            return self.hass.config_entries.async_get_known_entry(self.handler)

        def async_show_form(self, **kwargs):
            return kwargs

        def async_create_entry(self, title: str, data: dict[str, object]):
            return {"title": title, "data": data}

    config_entries_module = DummyModule(
        "homeassistant.config_entries",
        ConfigEntry=ConfigEntry,
        ConfigFlow=ConfigFlow,
        OptionsFlow=OptionsFlow,
    )

    class HomeAssistant:  # type: ignore[too-few-public-methods]
        pass

    core_module = DummyModule(
        "homeassistant.core",
        callback=lambda function: function,
        HomeAssistant=HomeAssistant,
    )

    class SelectSelectorMode:
        DROPDOWN = "dropdown"

    class SelectOptionDict(dict):
        def __init__(self, value: str, label: str) -> None:
            super().__init__(value=value, label=label)

    class SelectSelectorConfig:  # type: ignore[too-few-public-methods]
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class SelectSelector:  # type: ignore[too-few-public-methods]
        def __init__(self, config: SelectSelectorConfig) -> None:
            self.config = config

    selector_module = DummyModule(
        "homeassistant.helpers.selector",
        SelectSelector=SelectSelector,
        SelectSelectorConfig=SelectSelectorConfig,
        SelectOptionDict=SelectOptionDict,
        SelectSelectorMode=SelectSelectorMode,
    )

    helpers_module = DummyModule("homeassistant.helpers")
    helpers_module.selector = selector_module

    sys.modules["homeassistant"] = ha_module
    sys.modules["homeassistant.config_entries"] = config_entries_module
    sys.modules["homeassistant.core"] = core_module
    sys.modules["homeassistant.helpers"] = helpers_module
    sys.modules["homeassistant.helpers.selector"] = selector_module


from custom_components.entsoe_qh.config_flow import (  # noqa: E402  # isort:skip
    EntsoeConfigFlow,
    EntsoeOptionsFlow,
)


class DummyConfigEntry:
    def __init__(self, entry_id: str = "entry-1") -> None:
        self.entry_id = entry_id
        self.data: dict[str, object] = {}


class DummyConfigEntryManager:
    def __init__(self, entry: DummyConfigEntry) -> None:
        self._entry = entry

    def async_get_known_entry(self, entry_id: str) -> DummyConfigEntry:
        assert_that(entry_id).is_equal_to(self._entry.entry_id)
        return self._entry


def test_async_get_options_flow_provides_options_handler():
    # Arrange
    config_entry = DummyConfigEntry()

    # Act
    options_flow = EntsoeConfigFlow.async_get_options_flow(config_entry)
    options_flow.hass = DummyModule(
        "hass", config_entries=DummyConfigEntryManager(config_entry)
    )
    options_flow.handler = config_entry.entry_id

    # Assert
    assert_that(options_flow).is_instance_of(EntsoeOptionsFlow)
    assert_that(options_flow.config_entry).is_same_as(config_entry)
