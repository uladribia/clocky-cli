"""Contract tests for the real HTTP API adapter using mocked HTTP responses.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from clocky.domain.models import StartTimerRequest
from clocky.infra.api import ClockifyAPI, ClockifyAPIError


@pytest.fixture
def api() -> ClockifyAPI:
    """Create a Clockify API client bound to a fake base URL."""
    return ClockifyAPI(api_key="test-key", base_url="https://clocky.test")


def test_get_user_parses_response(api: ClockifyAPI, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://clocky.test/user",
        json={
            "id": "user-001",
            "name": "Test User",
            "email": "test@example.com",
            "defaultWorkspace": "ws-001",
        },
    )

    user = api.get_user()

    assert user.id == "user-001"
    assert user.default_workspace == "ws-001"


def test_get_time_entries_coerces_null_tag_ids(api: ClockifyAPI, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://clocky.test/workspaces/ws-001/user/user-001/time-entries?page-size=2",
        json=[
            {
                "id": "entry-001",
                "description": "Work",
                "projectId": "proj-001",
                "workspaceId": "ws-001",
                "userId": "user-001",
                "tagIds": None,
                "timeInterval": {
                    "start": "2026-03-29T10:00:00Z",
                    "end": "2026-03-29T11:00:00Z",
                    "duration": "PT1H",
                },
            }
        ],
    )

    entries = api.get_time_entries("ws-001", "user-001", limit=2)

    assert entries[0].tag_ids == []


def test_get_running_timer_returns_none_when_empty(api: ClockifyAPI, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://clocky.test/workspaces/ws-001/user/user-001/"
            "time-entries?in-progress=true&page-size=1"
        ),
        json=[],
    )

    running = api.get_running_timer("ws-001", "user-001")

    assert running is None


def test_start_timer_raises_clockify_api_error(api: ClockifyAPI, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://clocky.test/workspaces/ws-001/time-entries",
        status_code=400,
        json={"message": "Project is archived"},
    )

    with pytest.raises(ClockifyAPIError, match="Project is archived"):
        api.start_timer(
            "ws-001",
            StartTimerRequest(
                start="2026-03-29T10:00:00Z",
                description="Test",
                project_id="proj-archived",
            ),
        )
