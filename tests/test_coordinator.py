"""Tests for Watercryst coordinators."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.watercryst.api import (
    WatercrystAuthError,
    WatercrystEvent,
    WatercrystMode,
    WatercrystRateLimitError,
    WatercrystState,
    WatercrystStatistics,
    WatercrystStatisticsEntry,
    WatercrystWaterProtection,
)
from custom_components.watercryst.coordinator import (
    WatercrystStateCoordinator,
    WatercrystStatisticsCoordinator,
)


@pytest.mark.asyncio
async def test_state_coordinator_refresh_success(hass) -> None:
    """The state coordinator should store successful update data."""
    api = AsyncMock()
    api.async_get_state.return_value = WatercrystState(
        online=True,
        mode=WatercrystMode(id="WT", name="Water Treatment"),
        event=WatercrystEvent(),
        water_protection=WatercrystWaterProtection(absence_mode_enabled=True),
        ml_state="success",
    )
    coordinator = WatercrystStateCoordinator(hass, api, 300)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.online is True
    assert coordinator.data.absence_mode_enabled is True
    api.async_get_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_state_coordinator_raises_auth_failure(hass) -> None:
    """Authentication failures should surface as ConfigEntryAuthFailed."""
    api = AsyncMock()
    api.async_get_state.side_effect = WatercrystAuthError("bad key")
    coordinator = WatercrystStateCoordinator(hass, api, 300)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_state_coordinator_raises_update_failed_for_rate_limit(hass) -> None:
    """Rate limiting should become a recoverable UpdateFailed error."""
    api = AsyncMock()
    api.async_get_state.side_effect = WatercrystRateLimitError("slow down")
    coordinator = WatercrystStateCoordinator(hass, api, 300)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_statistics_coordinator_refresh_success(hass) -> None:
    """The statistics coordinator should store successful update data."""
    api = AsyncMock()
    api.async_get_statistics.return_value = WatercrystStatistics(
        type="statistics",
        entries=(
            WatercrystStatisticsEntry(
                consumption=12.34,
                timestamp=datetime.fromisoformat("2021-04-01T13:25:00"),
            ),
        ),
    )
    coordinator = WatercrystStatisticsCoordinator(hass, api)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.latest_entry is not None
    assert coordinator.data.latest_entry.consumption == 12.34
