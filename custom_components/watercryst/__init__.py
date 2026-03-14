"""The Watercryst integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from .const import CONF_API_KEY, DOMAIN, PLATFORMS, get_poll_interval

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import WatercrystApiClient
    from .coordinator import (
        WatercrystStateCoordinator,
        WatercrystStatisticsCoordinator,
    )

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class WatercrystRuntimeData:
    """Runtime data stored on the config entry."""

    api: WatercrystApiClient
    state_coordinator: WatercrystStateCoordinator
    statistics_coordinator: WatercrystStatisticsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Watercryst from a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import WatercrystApiClient
    from .coordinator import (
        WatercrystStateCoordinator,
        WatercrystStatisticsCoordinator,
    )

    api = WatercrystApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_API_KEY],
    )
    state_coordinator = WatercrystStateCoordinator(hass, api, get_poll_interval(entry))
    statistics_coordinator = WatercrystStatisticsCoordinator(hass, api)

    await state_coordinator.async_config_entry_first_refresh()
    await statistics_coordinator.async_refresh()

    if not statistics_coordinator.last_update_success:
        LOGGER.warning(
            "Initial Watercryst statistics refresh failed; statistics sensors will recover on the next scheduled refresh"
        )

    entry.runtime_data = WatercrystRuntimeData(
        api=api,
        state_coordinator=state_coordinator,
        statistics_coordinator=statistics_coordinator,
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
