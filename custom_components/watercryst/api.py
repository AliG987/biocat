"""API client for WATERCryst myBIOCAT."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
import json
from typing import Any, Mapping, Self

import aiohttp

from .const import API_BASE_URL, ML_STATE_LEAKAGE, MODE_WATER_SUPPLY_CLOSED


class WatercrystError(Exception):
    """Base error for Watercryst API failures."""


class WatercrystAuthError(WatercrystError):
    """Raised when the API key is invalid."""


class WatercrystForbiddenError(WatercrystError):
    """Raised when the account is not allowed to use the API."""


class WatercrystRateLimitError(WatercrystError):
    """Raised when the API returns HTTP 429."""


class WatercrystConnectionError(WatercrystError):
    """Raised when a network or timeout issue occurs."""


def _as_mapping(value: object) -> Mapping[str, Any]:
    """Return a mapping view of a JSON object."""
    if isinstance(value, Mapping):
        return value
    return {}


def _as_string(value: object) -> str | None:
    """Return a stripped string value if possible."""
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    return normalized or None


def _as_int(value: object) -> int | None:
    """Return an int value if possible."""
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None

    return None


def _as_float(value: object) -> float | None:
    """Return a float value if possible."""
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None

    return None


def _parse_datetime(value: object) -> datetime | None:
    """Parse an ISO datetime string into a datetime object."""
    timestamp = _as_string(value)
    if timestamp is None:
        return None

    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"

    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


@dataclass(slots=True, frozen=True)
class WatercrystMode:
    """Normalized device mode."""

    id: str | None = None
    name: str | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        """Build an instance from a JSON mapping."""
        return cls(
            id=_as_string(payload.get("id")),
            name=_as_string(payload.get("name")),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {"id": self.id, "name": self.name}


@dataclass(slots=True, frozen=True)
class WatercrystEvent:
    """Normalized current event."""

    event_id: int | None = None
    category: str | None = None
    title: str | None = None
    description: str | None = None
    timestamp: datetime | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        """Build an instance from a JSON mapping."""
        return cls(
            event_id=_as_int(payload.get("eventId")),
            category=_as_string(payload.get("category")),
            title=_as_string(payload.get("title")),
            description=_as_string(payload.get("description")),
            timestamp=_parse_datetime(payload.get("timestamp")),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "event_id": self.event_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass(slots=True, frozen=True)
class WatercrystWaterProtection:
    """Normalized water protection state."""

    absence_mode_enabled: bool = False
    pause_leakage_protection_until_utc: datetime | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        """Build an instance from a JSON mapping."""
        return cls(
            absence_mode_enabled=bool(payload.get("absenceModeEnabled")),
            pause_leakage_protection_until_utc=_parse_datetime(
                payload.get("pauseLeakageProtectionUntilUTC")
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "absence_mode_enabled": self.absence_mode_enabled,
            "pause_leakage_protection_until_utc": (
                self.pause_leakage_protection_until_utc.isoformat()
                if self.pause_leakage_protection_until_utc
                else None
            ),
        }


@dataclass(slots=True, frozen=True)
class WatercrystState:
    """Normalized device state."""

    online: bool
    mode: WatercrystMode
    event: WatercrystEvent
    water_protection: WatercrystWaterProtection
    ml_state: str | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        """Build an instance from a JSON mapping."""
        return cls(
            online=bool(payload.get("online")),
            mode=WatercrystMode.from_dict(_as_mapping(payload.get("mode"))),
            event=WatercrystEvent.from_dict(_as_mapping(payload.get("event"))),
            water_protection=WatercrystWaterProtection.from_dict(
                _as_mapping(payload.get("waterProtection"))
            ),
            ml_state=_as_string(payload.get("mlState")),
        )

    @property
    def absence_mode_enabled(self) -> bool:
        """Return whether absence mode is enabled."""
        return self.water_protection.absence_mode_enabled

    @property
    def water_supply_open(self) -> bool:
        """Return whether the water supply is currently open."""
        return self.mode.id != MODE_WATER_SUPPLY_CLOSED

    @property
    def leak_detected(self) -> bool:
        """Return whether a leak is currently detected."""
        return self.ml_state == ML_STATE_LEAKAGE

    @property
    def mode_label(self) -> str:
        """Return the best available mode label."""
        return self.mode.name or self.mode.id or "unknown"

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "online": self.online,
            "mode": self.mode.as_dict(),
            "event": self.event.as_dict(),
            "water_protection": self.water_protection.as_dict(),
            "ml_state": self.ml_state,
            "absence_mode_enabled": self.absence_mode_enabled,
            "water_supply_open": self.water_supply_open,
            "leak_detected": self.leak_detected,
        }


@dataclass(slots=True, frozen=True)
class WatercrystStatisticsEntry:
    """A single consumption statistics entry."""

    consumption: float
    timestamp: datetime

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "consumption": self.consumption,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(slots=True, frozen=True)
class WatercrystStatistics:
    """Normalized statistics response."""

    type: str | None
    entries: tuple[WatercrystStatisticsEntry, ...]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        """Build an instance from a JSON mapping."""
        parsed_entries: list[WatercrystStatisticsEntry] = []

        raw_entries = payload.get("entries")
        if isinstance(raw_entries, list):
            for raw_entry in raw_entries:
                entry_data = _as_mapping(raw_entry)
                consumption = _as_float(entry_data.get("consumption"))
                timestamp = _parse_datetime(entry_data.get("date"))

                if consumption is None or timestamp is None:
                    continue

                parsed_entries.append(
                    WatercrystStatisticsEntry(
                        consumption=consumption,
                        timestamp=timestamp,
                    )
                )

        parsed_entries.sort(key=lambda entry: entry.timestamp)

        return cls(
            type=_as_string(payload.get("type")),
            entries=tuple(parsed_entries),
        )

    @property
    def latest_entry(self) -> WatercrystStatisticsEntry | None:
        """Return the latest known statistics entry."""
        if not self.entries:
            return None
        return self.entries[-1]

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "type": self.type,
            "entries": [entry.as_dict() for entry in self.entries],
        }


class WatercrystApiClient:
    """Small aiohttp client for the Watercryst API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        *,
        base_url: str = API_BASE_URL,
        request_timeout: float = 15,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)

    @property
    def _headers(self) -> dict[str, str]:
        """Return request headers."""
        return {"X-API-KEY": self._api_key}

    async def async_get_state(self) -> WatercrystState:
        """Fetch the current device state."""
        payload = await self._async_request("/state", expect_json=True)
        return WatercrystState.from_dict(payload)

    async def async_get_statistics(self) -> WatercrystStatistics:
        """Fetch daily/direct statistics."""
        payload = await self._async_request("/statistics/daily/direct", expect_json=True)
        return WatercrystStatistics.from_dict(payload)

    async def async_enable_absence(self) -> None:
        """Enable absence mode."""
        await self._async_request("/absence/enable", expect_json=False)

    async def async_disable_absence(self) -> None:
        """Disable absence mode."""
        await self._async_request("/absence/disable", expect_json=False)

    async def async_open_water_supply(self) -> None:
        """Open the water supply."""
        await self._async_request("/watersupply/open", expect_json=False)

    async def async_close_water_supply(self) -> None:
        """Close the water supply."""
        await self._async_request("/watersupply/close", expect_json=False)

    async def _async_request(
        self,
        path: str,
        *,
        expect_json: bool,
    ) -> Mapping[str, Any]:
        """Run a GET request against the Watercryst API."""
        url = f"{self._base_url}{path}"

        try:
            async with self._session.get(
                url,
                headers=self._headers,
                timeout=self._timeout,
            ) as response:
                if response.status == HTTPStatus.UNAUTHORIZED:
                    raise WatercrystAuthError("Invalid Watercryst API key")

                if response.status == HTTPStatus.FORBIDDEN:
                    raise WatercrystForbiddenError(
                        "This Watercryst account is not allowed to use the API"
                    )

                if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                    raise WatercrystRateLimitError("Watercryst API rate limit reached")

                if response.status >= HTTPStatus.BAD_REQUEST:
                    raise WatercrystError(
                        f"Unexpected Watercryst API response: HTTP {response.status}"
                    )

                if not expect_json:
                    await response.read()
                    return {}

                try:
                    payload = await response.json(content_type=None)
                except (
                    aiohttp.ContentTypeError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as err:
                    raise WatercrystError(
                        "Malformed JSON received from the Watercryst API"
                    ) from err
        except asyncio.TimeoutError as err:
            raise WatercrystConnectionError(
                "Timed out while communicating with the Watercryst API"
            ) from err
        except aiohttp.ClientError as err:
            raise WatercrystConnectionError(
                "Error communicating with the Watercryst API"
            ) from err

        if not isinstance(payload, Mapping):
            raise WatercrystError(
                "Unexpected JSON structure received from the Watercryst API"
            )

        return payload
