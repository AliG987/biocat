"""Switch platform for Watercryst."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

from .api import (
    WatercrystApiClient,
    WatercrystAuthError,
    WatercrystConnectionError,
    WatercrystError,
    WatercrystRateLimitError,
    WatercrystState,
)
from .entity import WatercrystCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class WatercrystSwitchEntityDescription(SwitchEntityDescription):
    """Describe a Watercryst switch."""

    value_fn: Callable[[WatercrystState], bool]
    turn_on_fn: Callable[[WatercrystApiClient], Awaitable[None]]
    turn_off_fn: Callable[[WatercrystApiClient], Awaitable[None]]


SWITCH_DESCRIPTIONS: tuple[WatercrystSwitchEntityDescription, ...] = (
    WatercrystSwitchEntityDescription(
        key="absence_mode",
        translation_key="absence_mode",
        icon="mdi:home-lock",
        value_fn=lambda state: state.absence_mode_enabled,
        turn_on_fn=lambda api: api.async_enable_absence(),
        turn_off_fn=lambda api: api.async_disable_absence(),
    ),
    WatercrystSwitchEntityDescription(
        key="water_supply",
        translation_key="water_supply",
        icon="mdi:pipe-valve",
        value_fn=lambda state: state.water_supply_open,
        turn_on_fn=lambda api: api.async_open_water_supply(),
        turn_off_fn=lambda api: api.async_close_water_supply(),
    ),
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Watercryst switch entities."""
    runtime_data = entry.runtime_data
    async_add_entities(
        WatercrystSwitchEntity(entry, runtime_data.state_coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    )


class WatercrystSwitchEntity(WatercrystCoordinatorEntity, SwitchEntity):
    """Representation of a Watercryst switch."""

    entity_description: WatercrystSwitchEntityDescription

    def __init__(self, config_entry, coordinator, description) -> None:
        """Initialize the switch."""
        super().__init__(config_entry, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{config_entry.unique_id or config_entry.entry_id}_{description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the switch is on."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_run_action(self.entity_description.turn_on_fn)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_run_action(self.entity_description.turn_off_fn)

    async def _async_run_action(
        self,
        action: Callable[[WatercrystApiClient], Awaitable[None]],
    ) -> None:
        """Run a control action and refresh state."""
        try:
            await action(self.runtime_data.api)
        except WatercrystRateLimitError as err:
            raise HomeAssistantError(
                "Watercryst API rate limited the control request"
            ) from err
        except WatercrystAuthError as err:
            raise HomeAssistantError(
                "Watercryst authentication failed; reconfigure the integration"
            ) from err
        except WatercrystConnectionError as err:
            raise HomeAssistantError(
                "Unable to reach the Watercryst API"
            ) from err
        except WatercrystError as err:
            raise HomeAssistantError(str(err)) from err

        await self.runtime_data.state_coordinator.async_request_refresh()
