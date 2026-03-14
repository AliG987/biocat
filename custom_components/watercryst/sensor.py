"""Sensor platform for Watercryst."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import (
    WatercrystEvent,
    WatercrystState,
    WatercrystStatistics,
    WatercrystStatisticsEntry,
)
from .const import RECENT_STATISTICS_ENTRY_COUNT
from .entity import WatercrystCoordinatorEntity


def _local_date(value: datetime) -> date:
    """Return the Home Assistant local date for a timestamp."""
    if value.tzinfo is None:
        return value.date()
    return dt_util.as_local(value).date()


def _recent_entries(stats: WatercrystStatistics) -> list[dict[str, Any]]:
    """Return a compact list of recent statistics entries."""
    return [entry.as_dict() for entry in stats.entries[-RECENT_STATISTICS_ENTRY_COUNT:]]


def _yesterday_entry(
    stats: WatercrystStatistics,
    hass: HomeAssistant,
) -> WatercrystStatisticsEntry | None:
    """Return the latest entry that matches yesterday's local date."""
    timezone = dt_util.get_time_zone(hass.config.time_zone)
    today = dt_util.now(timezone).date() if timezone else dt_util.now().date()
    yesterday = today - timedelta(days=1)
    matching_entries = [
        entry for entry in stats.entries if _local_date(entry.timestamp) == yesterday
    ]
    if not matching_entries:
        return None
    return matching_entries[-1]


def _latest_entry_attributes(stats: WatercrystStatistics) -> dict[str, Any] | None:
    """Build attributes for the latest consumption sensor."""
    latest_entry = stats.latest_entry
    if latest_entry is None:
        return None

    return {
        "timestamp": latest_entry.timestamp.isoformat(),
        "recent_entries": _recent_entries(stats),
    }


def _latest_date_attributes(stats: WatercrystStatistics) -> dict[str, Any] | None:
    """Build attributes for the latest date sensor."""
    latest_entry = stats.latest_entry
    if latest_entry is None:
        return None

    return {"consumption": latest_entry.consumption}


def _yesterday_attributes(
    stats: WatercrystStatistics,
    hass: HomeAssistant,
) -> dict[str, Any] | None:
    """Build attributes for the yesterday consumption sensor."""
    yesterday = _yesterday_entry(stats, hass)
    if yesterday is None:
        return None

    return {"timestamp": yesterday.timestamp.isoformat()}


def _yesterday_consumption(
    stats: WatercrystStatistics,
    hass: HomeAssistant,
) -> float | None:
    """Return yesterday's consumption if available."""
    yesterday = _yesterday_entry(stats, hass)
    if yesterday is None:
        return None

    return yesterday.consumption


def _event_attributes(event: WatercrystEvent) -> dict[str, Any] | None:
    """Build event attributes."""
    attributes: dict[str, Any] = {}

    if event.event_id is not None:
        attributes["event_id"] = event.event_id
    if event.category is not None:
        attributes["category"] = event.category
    if event.description is not None:
        attributes["description"] = event.description
    if event.timestamp is not None:
        attributes["timestamp"] = event.timestamp.isoformat()

    return attributes or None


@dataclass(frozen=True, kw_only=True)
class WatercrystStateSensorEntityDescription(SensorEntityDescription):
    """Describe a Watercryst state-based sensor."""

    value_fn: Callable[[WatercrystState], str | datetime | float | None]
    attrs_fn: Callable[[WatercrystState], Mapping[str, Any] | None] = lambda state: None


@dataclass(frozen=True, kw_only=True)
class WatercrystStatisticsSensorEntityDescription(SensorEntityDescription):
    """Describe a Watercryst statistics sensor."""

    value_fn: Callable[[WatercrystStatistics, HomeAssistant], str | datetime | float | None]
    attrs_fn: Callable[
        [WatercrystStatistics, HomeAssistant],
        Mapping[str, Any] | None,
    ] = lambda stats, hass: None


STATE_SENSOR_DESCRIPTIONS: tuple[WatercrystStateSensorEntityDescription, ...] = (
    WatercrystStateSensorEntityDescription(
        key="mode",
        translation_key="mode",
        icon="mdi:water-sync",
        value_fn=lambda state: state.mode_label,
        attrs_fn=lambda state: {"mode_id": state.mode.id} if state.mode.id else None,
    ),
    WatercrystStateSensorEntityDescription(
        key="current_event",
        translation_key="current_event",
        icon="mdi:alert-circle-outline",
        value_fn=lambda state: state.event.title,
        attrs_fn=lambda state: _event_attributes(state.event),
    ),
)

STATISTICS_SENSOR_DESCRIPTIONS: tuple[WatercrystStatisticsSensorEntityDescription, ...] = (
    WatercrystStatisticsSensorEntityDescription(
        key="consumption_latest_l",
        translation_key="consumption_latest_l",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda stats, hass: (
            stats.latest_entry.consumption if stats.latest_entry else None
        ),
        attrs_fn=lambda stats, hass: _latest_entry_attributes(stats),
    ),
    WatercrystStatisticsSensorEntityDescription(
        key="consumption_latest_date",
        translation_key="consumption_latest_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda stats, hass: (
            stats.latest_entry.timestamp if stats.latest_entry else None
        ),
        attrs_fn=lambda stats, hass: _latest_date_attributes(stats),
    ),
    WatercrystStatisticsSensorEntityDescription(
        key="consumption_yesterday_l",
        translation_key="consumption_yesterday_l",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda stats, hass: _yesterday_consumption(stats, hass),
        attrs_fn=lambda stats, hass: _yesterday_attributes(stats, hass),
    ),
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Watercryst sensors."""
    runtime_data = entry.runtime_data

    entities = [
        *(
            WatercrystStateSensorEntity(
                entry,
                runtime_data.state_coordinator,
                description,
            )
            for description in STATE_SENSOR_DESCRIPTIONS
        ),
        *(
            WatercrystStatisticsSensorEntity(
                entry,
                runtime_data.statistics_coordinator,
                description,
            )
            for description in STATISTICS_SENSOR_DESCRIPTIONS
        ),
    ]

    async_add_entities(entities)


class WatercrystStateSensorEntity(WatercrystCoordinatorEntity, SensorEntity):
    """State-backed Watercryst sensor."""

    entity_description: WatercrystStateSensorEntityDescription

    def __init__(self, config_entry, coordinator, description) -> None:
        """Initialize the sensor."""
        super().__init__(config_entry, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{config_entry.unique_id or config_entry.entry_id}_{description.key}"
        )

    @property
    def native_value(self) -> str | datetime | float | None:
        """Return the native sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


class WatercrystStatisticsSensorEntity(WatercrystCoordinatorEntity, SensorEntity):
    """Statistics-backed Watercryst sensor."""

    entity_description: WatercrystStatisticsSensorEntityDescription

    def __init__(self, config_entry, coordinator, description) -> None:
        """Initialize the sensor."""
        super().__init__(config_entry, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{config_entry.unique_id or config_entry.entry_id}_{description.key}"
        )

    @property
    def native_value(self) -> str | datetime | float | None:
        """Return the native sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data, self.hass)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data, self.hass)
