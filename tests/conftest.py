"""Pytest configuration: stub out Home Assistant before any component import.

Uses a sys.meta_path finder that automatically creates stub modules for every
``homeassistant.*`` import so tests that only exercise pure-Python code (like
models.py) can run without a full HA installation.
"""
from __future__ import annotations

import enum
import importlib
import sys
import types
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec


class _Stub:
    """A catch-all stub that silently accepts arbitrary attribute access."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name: str) -> "_Stub":
        return _Stub()

    def __call__(self, *args, **kwargs) -> "_Stub":
        return _Stub()

    def __iter__(self):
        return iter([])

    def __bool__(self) -> bool:
        return False

    def __class_getitem__(cls, item):
        return cls


class _StubLoader(Loader):
    def create_module(self, spec):
        return None  # use default creation

    def exec_module(self, module):
        pass  # leave the module empty (attributes added below)


class _HAFinder(MetaPathFinder):
    """Auto-stubs every ``homeassistant.*`` and ``aiohttp``/``async_timeout`` module."""

    _PREFIXES = ("homeassistant", "aiohttp", "async_timeout")

    def find_spec(self, fullname, path, target=None):
        if any(fullname == p or fullname.startswith(p + ".") for p in self._PREFIXES):
            return ModuleSpec(fullname, _StubLoader(), is_package=True)
        return None


# Register the finder BEFORE any imports of the stubs happen.
sys.meta_path.insert(0, _HAFinder())


# ------------------------------------------------------------------
# Now import the real sub-module stubs so we can attach named attrs.
# ------------------------------------------------------------------
import importlib as _imp  # noqa: E402 (after meta-path setup)


def _get(name: str) -> types.ModuleType:
    """Import (or create) a stub module by full dotted name."""
    if name not in sys.modules:
        sys.modules[name] = _imp.import_module(name)
    return sys.modules[name]


# homeassistant.const
class _Platform(str, enum.Enum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"


_const = _get("homeassistant.const")
_const.Platform = _Platform  # type: ignore[attr-defined]
_const.CONF_PASSWORD = "password"  # type: ignore[attr-defined]
_const.CONF_USERNAME = "username"  # type: ignore[attr-defined]

# homeassistant.exceptions
_exc = _get("homeassistant.exceptions")
_exc.ConfigEntryAuthFailed = Exception  # type: ignore[attr-defined]
_exc.ConfigEntryNotReady = Exception  # type: ignore[attr-defined]

# homeassistant.helpers.update_coordinator
_coord = _get("homeassistant.helpers.update_coordinator")
_coord.DataUpdateCoordinator = _Stub  # type: ignore[attr-defined]
_coord.UpdateFailed = Exception  # type: ignore[attr-defined]

# homeassistant.helpers.entity
_ent = _get("homeassistant.helpers.entity")
_ent.Entity = _Stub  # type: ignore[attr-defined]

# homeassistant.helpers.update_coordinator (CoordinatorEntity)
_coord.CoordinatorEntity = _Stub  # type: ignore[attr-defined]

# homeassistant.helpers.device_registry
_dr = _get("homeassistant.helpers.device_registry")
_dr.DeviceInfo = dict  # type: ignore[attr-defined]

# homeassistant.components.sensor
_sensor = _get("homeassistant.components.sensor")
_sensor.SensorEntity = _Stub  # type: ignore[attr-defined]
_sensor.SensorEntityDescription = _Stub  # type: ignore[attr-defined]

# homeassistant.components.binary_sensor
_binary = _get("homeassistant.components.binary_sensor")
_binary.BinarySensorEntity = _Stub  # type: ignore[attr-defined]
_binary.BinarySensorEntityDescription = _Stub  # type: ignore[attr-defined]

# homeassistant.config_entries
_ce = _get("homeassistant.config_entries")
_ce.ConfigFlow = _Stub  # type: ignore[attr-defined]
_ce.OptionsFlow = _Stub  # type: ignore[attr-defined]

# homeassistant.helpers.selector
_sel = _get("homeassistant.helpers.selector")
_sel.selector = _Stub()  # type: ignore[attr-defined]
_sel.TextSelector = _Stub  # type: ignore[attr-defined]
_sel.TextSelectorConfig = _Stub  # type: ignore[attr-defined]

# aiohttp
_aiohttp = _get("aiohttp")
_aiohttp.ClientSession = _Stub  # type: ignore[attr-defined]
_aiohttp.ClientError = Exception  # type: ignore[attr-defined]
_aiohttp.ClientResponse = _Stub  # type: ignore[attr-defined]

# async_timeout
_at = _get("async_timeout")
_at.timeout = _Stub  # type: ignore[attr-defined]
