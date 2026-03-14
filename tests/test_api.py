"""Tests for the Watercryst API client."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any

import aiohttp
import pytest

from custom_components.watercryst.api import (
    WatercrystApiClient,
    WatercrystAuthError,
    WatercrystConnectionError,
    WatercrystError,
    WatercrystForbiddenError,
    WatercrystRateLimitError,
)


class MockResponse:
    """Minimal aiohttp response context manager for tests."""

    def __init__(
        self,
        *,
        status: int = 200,
        json_data: Any = None,
        json_exception: Exception | None = None,
    ) -> None:
        """Initialize the mock response."""
        self.status = status
        self._json_data = json_data
        self._json_exception = json_exception

    async def __aenter__(self) -> MockResponse:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Exit the async context manager."""
        return None

    async def json(self, content_type: str | None = None) -> Any:
        """Return JSON data or raise the configured exception."""
        if self._json_exception is not None:
            raise self._json_exception
        return self._json_data

    async def read(self) -> bytes:
        """Return an empty body."""
        return b""


class MockSession:
    """Minimal aiohttp ClientSession stand-in."""

    def __init__(
        self,
        *,
        responses: list[MockResponse] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Initialize the mock session."""
        self._responses = responses or []
        self._exception = exception
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> MockResponse:
        """Return the next response or raise the configured exception."""
        self.calls.append({"url": url, **kwargs})

        if self._exception is not None:
            raise self._exception

        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_async_get_state_parses_success_response() -> None:
    """The client should normalize a successful state response."""
    session = MockSession(
        responses=[
            MockResponse(
                json_data={
                    "online": True,
                    "mode": {"id": "WT", "name": "Water Treatment"},
                    "event": {
                        "eventId": 10,
                        "category": "warning",
                        "title": "Granulate change due",
                        "description": "The granulate has expired.",
                        "timestamp": "2021-04-01T13:25:00",
                    },
                    "waterProtection": {"absenceModeEnabled": True},
                    "mlState": "success",
                }
            )
        ]
    )
    client = WatercrystApiClient(session, "secret")

    state = await client.async_get_state()

    assert state.online is True
    assert state.mode.id == "WT"
    assert state.mode_label == "Water Treatment"
    assert state.absence_mode_enabled is True
    assert state.water_supply_open is True
    assert state.leak_detected is False
    assert state.event.title == "Granulate change due"
    assert state.event.timestamp == datetime.fromisoformat("2021-04-01T13:25:00")
    assert session.calls[0]["url"].endswith("/state")
    assert session.calls[0]["headers"]["X-API-KEY"] == "secret"


@pytest.mark.asyncio
async def test_async_get_state_handles_missing_nested_objects() -> None:
    """Missing event and waterProtection objects should not break parsing."""
    session = MockSession(
        responses=[
            MockResponse(
                json_data={
                    "online": False,
                    "mode": {"id": "WO"},
                    "event": {},
                    "waterProtection": None,
                    "mlState": "leakage",
                }
            )
        ]
    )
    client = WatercrystApiClient(session, "secret")

    state = await client.async_get_state()

    assert state.online is False
    assert state.absence_mode_enabled is False
    assert state.water_supply_open is False
    assert state.leak_detected is True
    assert state.event.title is None
    assert state.event.timestamp is None


@pytest.mark.asyncio
async def test_async_get_statistics_sorts_entries_by_timestamp() -> None:
    """Statistics should be sorted chronologically and expose the latest entry."""
    session = MockSession(
        responses=[
            MockResponse(
                json_data={
                    "type": "statistics",
                    "entries": [
                        {
                            "consumption": 12.3,
                            "date": "2021-04-03T13:25:00",
                        },
                        {
                            "consumption": 10.0,
                            "date": "2021-04-01T13:25:00",
                        },
                        {
                            "consumption": 11.1,
                            "date": "2021-04-02T13:25:00",
                        },
                    ],
                }
            )
        ]
    )
    client = WatercrystApiClient(session, "secret")

    statistics = await client.async_get_statistics()

    assert [entry.consumption for entry in statistics.entries] == [10.0, 11.1, 12.3]
    assert statistics.latest_entry is not None
    assert statistics.latest_entry.consumption == 12.3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_exception"),
    [
        (401, WatercrystAuthError),
        (403, WatercrystForbiddenError),
        (429, WatercrystRateLimitError),
    ],
)
async def test_async_get_state_raises_for_known_http_errors(
    status: int,
    expected_exception: type[Exception],
) -> None:
    """The client should translate important HTTP status codes."""
    session = MockSession(responses=[MockResponse(status=status, json_data={})])
    client = WatercrystApiClient(session, "secret")

    with pytest.raises(expected_exception):
        await client.async_get_state()


@pytest.mark.asyncio
async def test_async_get_state_raises_connection_error_for_client_failures() -> None:
    """Client-side aiohttp failures should map to WatercrystConnectionError."""
    session = MockSession(exception=aiohttp.ClientError("boom"))
    client = WatercrystApiClient(session, "secret")

    with pytest.raises(WatercrystConnectionError):
        await client.async_get_state()


@pytest.mark.asyncio
async def test_async_get_state_raises_for_malformed_json() -> None:
    """Malformed JSON payloads should raise a Watercryst error."""
    session = MockSession(
        responses=[
            MockResponse(
                json_exception=json.JSONDecodeError("bad json", doc="", pos=0)
            )
        ]
    )
    client = WatercrystApiClient(session, "secret")

    with pytest.raises(WatercrystError):
        await client.async_get_state()
