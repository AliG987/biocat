"""Binary sensor platform for Watercryst."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .api import WatercrystState
from .entity import WatercrystCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class WatercrystBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a Watercryst binary sensor."""

    value_fn: Callable[[WatercrystState], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[WatercrystBinarySensorEntityDescription, ...] = (
    WatercrystBinarySensorEntityDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda state: state.online,
    ),
    WatercrystBinarySensorEntityDescription(
        key="leak_detected",
        translation_key="leak_detected",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda state: state.leak_detected,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Watercryst binary sensors."""
    runtime_data = entry.runtime_data
    async_add_entities(
        WatercrystBinarySensorEntity(
            entry,
            runtime_data.state_coordinator,
            description,
        )
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class WatercrystBinarySensorEntity(WatercrystCoordinatorEntity, BinarySensorEntity):
    """Representation of a Watercryst binary sensor."""

    entity_description: WatercrystBinarySensorEntityDescription

    def __init__(self, config_entry, coordinator, description) -> None:
        """Initialize the binary sensor."""
        super().__init__(config_entry, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{config_entry.unique_id or config_entry.entry_id}_{description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
