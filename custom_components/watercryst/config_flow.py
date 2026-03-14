"""Config flow for the Watercryst integration."""

from __future__ import annotations

from collections.abc import Mapping

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WatercrystApiClient,
    WatercrystAuthError,
    WatercrystConnectionError,
    WatercrystError,
    WatercrystForbiddenError,
    WatercrystRateLimitError,
)
from .const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_POLL_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MIN_POLL_INTERVAL,
    build_account_id,
    get_display_name,
    get_poll_interval,
)


def _normalize_name(value: object) -> str:
    """Normalize a user-provided display name."""
    if not isinstance(value, str):
        return DEFAULT_NAME

    normalized = value.strip()
    return normalized or DEFAULT_NAME


def _schema_defaults(data: Mapping[str, object] | None = None) -> dict[str, object]:
    """Build schema defaults."""
    values = dict(data or {})
    values.setdefault(CONF_NAME, DEFAULT_NAME)
    values.setdefault(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    return values


def _build_user_schema(data: Mapping[str, object] | None = None) -> vol.Schema:
    """Build the user-step schema."""
    values = _schema_defaults(data)
    return vol.Schema(
        {
            vol.Required(
                CONF_API_KEY,
                default=str(values.get(CONF_API_KEY, "")),
            ): vol.All(str, vol.Length(min=1)),
            vol.Optional(
                CONF_NAME,
                default=str(values[CONF_NAME]),
            ): str,
            vol.Optional(
                CONF_POLL_INTERVAL,
                default=int(values[CONF_POLL_INTERVAL]),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL)),
        }
    )


def _build_options_schema(current_name: str, current_poll_interval: int) -> vol.Schema:
    """Build the options schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_NAME, default=current_name): str,
            vol.Optional(
                CONF_POLL_INTERVAL,
                default=current_poll_interval,
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL)),
        }
    )


class WatercrystConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Watercryst."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        form_input = dict(user_input or {})

        if user_input is not None:
            api_key = str(user_input[CONF_API_KEY]).strip()
            display_name = _normalize_name(user_input.get(CONF_NAME))
            poll_interval = int(user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))

            form_input = {
                CONF_API_KEY: api_key,
                CONF_NAME: display_name,
                CONF_POLL_INTERVAL: poll_interval,
            }

            await self.async_set_unique_id(build_account_id(api_key))
            self._abort_if_unique_id_configured()

            client = WatercrystApiClient(async_get_clientsession(self.hass), api_key)

            try:
                await client.async_get_state()
            except WatercrystAuthError:
                errors["base"] = "invalid_auth"
            except WatercrystForbiddenError:
                errors["base"] = "not_supported"
            except WatercrystRateLimitError:
                errors["base"] = "rate_limited"
            except WatercrystConnectionError:
                errors["base"] = "cannot_connect"
            except WatercrystError:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=display_name,
                    data=form_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_user_schema(form_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return WatercrystOptionsFlow(config_entry)


class WatercrystOptionsFlow(OptionsFlowWithReload):
    """Handle Watercryst options."""

    def __init__(self, config_entry) -> None:
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, object] | None = None,
    ) -> FlowResult:
        """Manage Watercryst options."""
        if user_input is not None:
            display_name = _normalize_name(user_input.get(CONF_NAME))
            poll_interval = int(
                user_input.get(CONF_POLL_INTERVAL, get_poll_interval(self.config_entry))
            )

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=display_name,
            )

            return self.async_create_entry(
                title="",
                data={
                    CONF_NAME: display_name,
                    CONF_POLL_INTERVAL: poll_interval,
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(
                get_display_name(self.config_entry),
                get_poll_interval(self.config_entry),
            ),
        )
