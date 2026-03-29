# SPDX-License-Identifier: MIT
"""Protocol definitions for Clockify access.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typing import Protocol

from clocky.domain.models import (
    Client,
    Project,
    StartTimerRequest,
    StopTimerRequest,
    Tag,
    TimeEntry,
    User,
    Workspace,
)


class ClockifyGateway(Protocol):
    """Typed boundary used by application and CLI code.

    Production code uses :class:`clocky.infra.api.ClockifyAPI`. Tests can provide any
    object implementing the same methods without inheriting from the production
    client.
    """

    def get_user(self) -> User:
        """Fetch the authenticated user."""

    def get_workspaces(self) -> list[Workspace]:
        """Fetch all workspaces."""

    def get_projects(self, workspace_id: str) -> list[Project]:
        """Fetch workspace projects."""

    def get_clients(self, workspace_id: str) -> list[Client]:
        """Fetch workspace clients."""

    def get_tags(self, workspace_id: str) -> list[Tag]:
        """Fetch workspace tags."""

    def get_time_entries(self, workspace_id: str, user_id: str, limit: int = 10) -> list[TimeEntry]:
        """Fetch recent time entries."""

    def get_running_timer(self, workspace_id: str, user_id: str) -> TimeEntry | None:
        """Fetch the current running timer, if any."""

    def start_timer(self, workspace_id: str, request: StartTimerRequest) -> TimeEntry:
        """Start a new timer."""

    def stop_timer(self, workspace_id: str, user_id: str, request: StopTimerRequest) -> TimeEntry:
        """Stop the current running timer."""

    def delete_time_entry(self, workspace_id: str, entry_id: str) -> None:
        """Delete a time entry."""

    def close(self) -> None:
        """Release any underlying resources."""
