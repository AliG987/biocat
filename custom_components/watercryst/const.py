"""Constants for the Watercryst integration."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Final

DOMAIN: Final = "watercryst"
PLATFORMS: Final = ("switch", "binary_sensor", "sensor")

CONF_API_KEY: Final = "api_key"
CONF_NAME: Final = "name"
CONF_POLL_INTERVAL: Final = "poll_interval"

DEFAULT_NAME: Final = "Watercryst"
DEFAULT_POLL_INTERVAL: Final = 300
MIN_POLL_INTERVAL: Final = 60

API_BASE_URL: Final = "https://appapi.watercryst.com/v1"

MANUFACTURER: Final = "WATERCryst"
MODEL: Final = "myBIOCAT"

MODE_WATER_SUPPLY_CLOSED: Final = "WO"
ML_STATE_LEAKAGE: Final = "leakage"

RECENT_STATISTICS_ENTRY_COUNT: Final = 7


def build_account_id(api_key: str) -> str:
    """Build a stable opaque identifier from the API key."""
    return sha256(api_key.strip().encode("utf-8")).hexdigest()[:16]


def get_display_name(config_entry: Any) -> str:
    """Return the resolved display name for a config entry."""
    value = config_entry.options.get(
        CONF_NAME,
        config_entry.data.get(CONF_NAME, DEFAULT_NAME),
    )
    if not isinstance(value, str):
        return DEFAULT_NAME

    normalized = value.strip()
    return normalized or DEFAULT_NAME


def get_poll_interval(config_entry: Any) -> int:
    """Return the resolved poll interval for a config entry."""
    raw_value = config_entry.options.get(
        CONF_POLL_INTERVAL,
        config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
    )

    try:
        poll_interval = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_POLL_INTERVAL

    return max(MIN_POLL_INTERVAL, poll_interval)
