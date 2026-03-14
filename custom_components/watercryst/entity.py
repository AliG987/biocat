"""Shared entity helpers for Watercryst."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystRuntimeData
from .const import DOMAIN, MANUFACTURER, MODEL, get_display_name


class WatercrystCoordinatorEntity(CoordinatorEntity[Any]):
    """Base entity class for Watercryst coordinator-backed entities."""

    _attr_has_entity_name = True

    def __init__(self, config_entry, coordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def runtime_data(self) -> WatercrystRuntimeData:
        """Return the runtime data attached to the config entry."""
        return self._config_entry.runtime_data

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared device information."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, self._config_entry.unique_id or self._config_entry.entry_id)
            },
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=get_display_name(self._config_entry),
        )

    async def async_update(self) -> None:
        """Manually refresh entity data."""
        await self.coordinator.async_request_refresh()
