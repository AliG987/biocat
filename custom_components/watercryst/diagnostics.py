"""Diagnostics support for Watercryst."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, get_display_name, get_poll_interval

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry,
):
    """Return diagnostics for a config entry."""
    runtime_data = config_entry.runtime_data

    return {
        "config_entry": async_redact_data(
            {
                "entry_id": config_entry.entry_id,
                "title": config_entry.title,
                "unique_id": config_entry.unique_id,
                "data": dict(config_entry.data),
                "options": dict(config_entry.options),
                "resolved_name": get_display_name(config_entry),
                "resolved_poll_interval": get_poll_interval(config_entry),
            },
            TO_REDACT,
        ),
        "state_last_update_success": runtime_data.state_coordinator.last_update_success,
        "state": (
            runtime_data.state_coordinator.data.as_dict()
            if runtime_data.state_coordinator.data
            else None
        ),
        "statistics_last_update_success": (
            runtime_data.statistics_coordinator.last_update_success
        ),
        "statistics": (
            runtime_data.statistics_coordinator.data.as_dict()
            if runtime_data.statistics_coordinator.data
            else None
        ),
    }
