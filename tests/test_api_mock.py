"""Tests for MockClockifyAPI."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from clocky.models import StartTimerRequest, StopTimerRequest
from clocky.testing import (
    MOCK_CLIENTS,
    MOCK_PROJECTS,
    MOCK_TIME_ENTRIES,
    MOCK_USER,
    MockClockifyAPI,
)


@pytest.fixture
def api() -> MockClockifyAPI:
    """Mock API with no running timer."""
    return MockClockifyAPI()


@pytest.fixture
def api_with_timer() -> MockClockifyAPI:
    """Mock API with a pre-set running timer."""
    return MockClockifyAPI(running_timer=MOCK_TIME_ENTRIES[0])


class TestGetters:
    """Tests for read-only mock methods."""

    def test_get_user(self, api: MockClockifyAPI) -> None:
        user = api.get_user()
        assert user.id == MOCK_USER.id
        assert user.email == MOCK_USER.email

    def test_get_workspaces(self, api: MockClockifyAPI) -> None:
        workspaces = api.get_workspaces()
        assert len(workspaces) >= 1
        assert workspaces[0].id == "ws-001"

    def test_get_projects(self, api: MockClockifyAPI) -> None:
        projects = api.get_projects("ws-001")
        assert len(projects) == len(MOCK_PROJECTS)

    def test_get_clients(self, api: MockClockifyAPI) -> None:
        clients = api.get_clients("ws-001")
        assert len(clients) == len(MOCK_CLIENTS)

    def test_get_tags(self, api: MockClockifyAPI) -> None:
        tags = api.get_tags("ws-001")
        assert len(tags) == 2

    def test_get_time_entries_default(self, api: MockClockifyAPI) -> None:
        entries = api.get_time_entries("ws-001", "user-001")
        assert len(entries) <= 10

    def test_get_time_entries_limit(self, api: MockClockifyAPI) -> None:
        entries = api.get_time_entries("ws-001", "user-001", limit=1)
        assert len(entries) == 1

    def test_running_timer_none(self, api: MockClockifyAPI) -> None:
        assert api.get_running_timer("ws-001", "user-001") is None

    def test_running_timer_active(self, api_with_timer: MockClockifyAPI) -> None:
        result = api_with_timer.get_running_timer("ws-001", "user-001")
        assert result is not None
        assert result.id == MOCK_TIME_ENTRIES[0].id


class TestStartTimer:
    """Tests for start_timer."""

    def test_start_sets_running(self, api: MockClockifyAPI) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        req = StartTimerRequest(start=now, description="Test", project_id="proj-001")
        entry = api.start_timer("ws-001", req)
        assert entry.id == "entry-new"
        assert entry.description == "Test"
        assert entry.project_id == "proj-001"

    def test_start_no_project(self, api: MockClockifyAPI) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = api.start_timer("ws-001", StartTimerRequest(start=now))
        assert entry.project_id is None

    def test_start_with_tags(self, api: MockClockifyAPI) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        req = StartTimerRequest(start=now, tag_ids=["tag-001", "tag-002"])
        entry = api.start_timer("ws-001", req)
        assert "tag-001" in entry.tag_ids


class TestStopTimer:
    """Tests for stop_timer."""

    def test_stop_clears_running(self, api_with_timer: MockClockifyAPI) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        api_with_timer.stop_timer("ws-001", "user-001", StopTimerRequest(end=now))
        assert api_with_timer.get_running_timer("ws-001", "user-001") is None

    def test_stop_no_running_raises(self, api: MockClockifyAPI) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with pytest.raises(ValueError, match="No timer"):
            api.stop_timer("ws-001", "user-001", StopTimerRequest(end=now))

    def test_stop_returns_with_end(self, api_with_timer: MockClockifyAPI) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        stopped = api_with_timer.stop_timer("ws-001", "user-001", StopTimerRequest(end=now))
        assert stopped.time_interval.end is not None
