"""Coordinators for the Watercryst integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import NoReturn

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WatercrystApiClient,
    WatercrystAuthError,
    WatercrystConnectionError,
    WatercrystError,
    WatercrystForbiddenError,
    WatercrystRateLimitError,
    WatercrystState,
    WatercrystStatistics,
)
from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


def _raise_update_error(refresh_name: str, err: WatercrystError) -> NoReturn:
    """Translate API exceptions into coordinator exceptions."""
    if isinstance(err, WatercrystAuthError):
        raise ConfigEntryAuthFailed("Watercryst authentication failed") from err

    if isinstance(err, WatercrystRateLimitError):
        LOGGER.warning(
            "Watercryst API rate limited the %s refresh; waiting for the next scheduled update",
            refresh_name,
        )
        raise UpdateFailed("Watercryst API rate limited the request") from err

    if isinstance(err, WatercrystForbiddenError):
        raise UpdateFailed(
            "This Watercryst account is not allowed to use the API"
        ) from err

    if isinstance(err, WatercrystConnectionError):
        raise UpdateFailed("Unable to reach the Watercryst API") from err

    raise UpdateFailed(str(err)) from err


class WatercrystStateCoordinator(DataUpdateCoordinator[WatercrystState]):
    """Coordinator for the device state endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: WatercrystApiClient,
        poll_interval_seconds: int,
    ) -> None:
        """Initialize the state coordinator."""
        self.api = api
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_state",
            update_interval=timedelta(seconds=poll_interval_seconds),
            always_update=False,
        )

    async def _async_update_data(self) -> WatercrystState:
        """Fetch the latest state."""
        try:
            return await self.api.async_get_state()
        except WatercrystError as err:
            _raise_update_error("state", err)


class WatercrystStatisticsCoordinator(DataUpdateCoordinator[WatercrystStatistics]):
    """Coordinator for daily/direct statistics."""

    def __init__(self, hass: HomeAssistant, api: WatercrystApiClient) -> None:
        """Initialize the statistics coordinator."""
        self.api = api
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_statistics",
            update_interval=timedelta(days=1),
            always_update=False,
        )

    async def _async_update_data(self) -> WatercrystStatistics:
        """Fetch the latest statistics."""
        try:
            return await self.api.async_get_statistics()
        except WatercrystError as err:
            _raise_update_error("statistics", err)
