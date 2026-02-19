"""Mock API and test fixtures for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime

from clocky.api import ClockifyAPI
from clocky.models import (
    Client,
    Project,
    StartTimerRequest,
    StopTimerRequest,
    Tag,
    TimeEntry,
    User,
    Workspace,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

MOCK_USER = User.model_validate(
    {
        "id": "user-001",
        "name": "Test User",
        "email": "test@example.com",
        "defaultWorkspace": "ws-001",
    }
)

MOCK_WORKSPACES = [Workspace(id="ws-001", name="My Workspace")]

MOCK_CLIENTS = [
    Client.model_validate({"id": "cli-001", "name": "Acme Corp", "workspaceId": "ws-001"}),
    Client.model_validate({"id": "cli-002", "name": "Globex Inc", "workspaceId": "ws-001"}),
]

MOCK_PROJECTS = [
    Project.model_validate(
        {
            "id": "proj-001",
            "name": "Website Redesign",
            "clientId": "cli-001",
            "clientName": "Acme Corp",
        }
    ),
    Project.model_validate(
        {
            "id": "proj-002",
            "name": "Mobile App",
            "clientId": "cli-001",
            "clientName": "Acme Corp",
        }
    ),
    Project.model_validate(
        {
            "id": "proj-003",
            "name": "Data Pipeline",
            "clientId": "cli-002",
            "clientName": "Globex Inc",
        }
    ),
    Project.model_validate(
        {
            "id": "proj-004",
            "name": "Internal Tools",
            "clientId": None,
            "clientName": None,
        }
    ),
    Project.model_validate(
        {
            "id": "proj-005",
            "name": "Data Pipe New",
            "clientId": "cli-002",
            "clientName": "Globex Inc",
        }
    ),
]

MOCK_TAGS = [
    Tag.model_validate({"id": "tag-001", "name": "billable", "workspaceId": "ws-001"}),
    Tag.model_validate({"id": "tag-002", "name": "meeting", "workspaceId": "ws-001"}),
]

MOCK_TIME_ENTRIES = [
    TimeEntry.model_validate(
        {
            "id": "entry-001",
            "description": "Fix login bug",
            "projectId": "proj-001",
            "workspaceId": "ws-001",
            "userId": "user-001",
            "tagIds": ["tag-001"],
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T11:00:00Z",
                "duration": "PT2H",
            },
        }
    ),
    TimeEntry.model_validate(
        {
            "id": "entry-002",
            "description": "Team standup",
            "projectId": "proj-002",
            "workspaceId": "ws-001",
            "userId": "user-001",
            "tagIds": ["tag-002"],
            "timeInterval": {
                "start": "2024-01-15T11:30:00Z",
                "end": "2024-01-15T12:00:00Z",
                "duration": "PT30M",
            },
        }
    ),
]


# -----------------------------------------------------------------------------
# Mock API
# -----------------------------------------------------------------------------


class MockClockifyAPI(ClockifyAPI):
    """Offline mock of ClockifyAPI for testing. Returns fixture data, no network calls."""

    def __init__(self, running_timer: TimeEntry | None = None) -> None:
        """Create mock API.

        Args:
            running_timer: Optional TimeEntry to return as the active timer.

        """
        # Skip parent __init__ — no HTTP client needed
        self._running_timer = running_timer

    def get_user(self) -> User:
        """Return mock user."""
        return MOCK_USER

    def get_workspaces(self) -> list[Workspace]:
        """Return mock workspaces."""
        return MOCK_WORKSPACES

    def get_projects(self, workspace_id: str) -> list[Project]:
        """Return mock projects."""
        del workspace_id  # unused
        return MOCK_PROJECTS

    def get_clients(self, workspace_id: str) -> list[Client]:
        """Return mock clients."""
        del workspace_id  # unused
        return MOCK_CLIENTS

    def get_tags(self, workspace_id: str) -> list[Tag]:
        """Return mock tags."""
        del workspace_id  # unused
        return MOCK_TAGS

    def get_time_entries(
        self,
        workspace_id: str,
        user_id: str,
        limit: int = 10,
    ) -> list[TimeEntry]:
        """Return mock time entries."""
        del workspace_id, user_id  # unused
        return MOCK_TIME_ENTRIES[:limit]

    def get_running_timer(self, workspace_id: str, user_id: str) -> TimeEntry | None:
        """Return the configured running timer."""
        del workspace_id, user_id  # unused
        return self._running_timer

    def start_timer(self, workspace_id: str, request: StartTimerRequest) -> TimeEntry:
        """Simulate starting a timer."""
        del workspace_id  # unused
        entry = TimeEntry.model_validate(
            {
                "id": "entry-new",
                "description": request.description,
                "projectId": request.project_id,
                "workspaceId": "ws-001",
                "userId": "user-001",
                "tagIds": request.tag_ids,
                "timeInterval": {"start": request.start, "end": None, "duration": None},
            }
        )
        self._running_timer = entry
        return entry

    def stop_timer(
        self,
        workspace_id: str,
        user_id: str,
        request: StopTimerRequest,
    ) -> TimeEntry:
        """Simulate stopping the running timer."""
        del workspace_id, user_id  # unused
        if self._running_timer is None:
            raise ValueError("No timer is currently running.")
        end_dt = datetime.fromisoformat(request.end.replace("Z", "+00:00"))
        stopped = self._running_timer.model_copy(
            update={
                "time_interval": self._running_timer.time_interval.model_copy(
                    update={"end": end_dt}
                )
            }
        )
        self._running_timer = None
        return stopped

    def delete_time_entry(self, workspace_id: str, entry_id: str) -> None:
        """Simulate deleting a time entry."""
        del workspace_id, entry_id  # unused

    def close(self) -> None:
        """No-op for mock."""
