# SPDX-License-Identifier: MIT
"""Clockify API client.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

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

BASE_URL = "https://api.clockify.me/api/v1"


class ClockifyAPI:
    """HTTP client for the Clockify REST API.

    Authenticates via X-Api-Key header. Methods raise httpx.HTTPStatusError on failure.
    """

    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        """Create a new API client.

        Args:
            api_key: Your Clockify API key.
            base_url: API base URL (override for testing).

        """
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            timeout=10.0,
        )

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _get(self, url: str, *, params: dict[str, str | int] | None = None) -> Any:
        """Execute a GET request and return the parsed JSON body."""
        r = self._client.get(url, params=params)
        r.raise_for_status()
        return r.json()

    def _get_list[T: BaseModel](
        self,
        url: str,
        model: type[T],
        *,
        params: dict[str, str | int] | None = None,
    ) -> list[T]:
        """Execute a GET request and validate the JSON array as a list of models."""
        return [model.model_validate(item) for item in self._get(url, params=params)]

    # -------------------------------------------------------------------------
    # User & Workspace
    # -------------------------------------------------------------------------

    def get_user(self) -> User:
        """Fetch the authenticated user."""
        return User.model_validate(self._get("/user"))

    def get_workspaces(self) -> list[Workspace]:
        """Fetch all workspaces the user belongs to."""
        return self._get_list("/workspaces", Workspace)

    # -------------------------------------------------------------------------
    # Projects, Clients, Tags
    # -------------------------------------------------------------------------

    def get_projects(self, workspace_id: str) -> list[Project]:
        """Fetch all projects in a workspace."""
        return self._get_list(
            f"/workspaces/{workspace_id}/projects", Project, params={"page-size": 500}
        )

    def get_clients(self, workspace_id: str) -> list[Client]:
        """Fetch all clients in a workspace."""
        return self._get_list(
            f"/workspaces/{workspace_id}/clients", Client, params={"page-size": 500}
        )

    def get_tags(self, workspace_id: str) -> list[Tag]:
        """Fetch all tags in a workspace."""
        return self._get_list(f"/workspaces/{workspace_id}/tags", Tag)

    # -------------------------------------------------------------------------
    # Time Entries
    # -------------------------------------------------------------------------

    def get_time_entries(
        self,
        workspace_id: str,
        user_id: str,
        limit: int = 10,
    ) -> list[TimeEntry]:
        """Fetch recent time entries for a user."""
        return self._get_list(
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            TimeEntry,
            params={"page-size": limit},
        )

    def get_running_timer(self, workspace_id: str, user_id: str) -> TimeEntry | None:
        """Fetch the currently running time entry, or None if no timer is active."""
        entries = self._get(
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            params={"in-progress": "true", "page-size": 1},
        )
        return TimeEntry.model_validate(entries[0]) if entries else None

    def start_timer(self, workspace_id: str, request: StartTimerRequest) -> TimeEntry:
        """Start a new time entry."""
        r = self._client.post(
            f"/workspaces/{workspace_id}/time-entries",
            json=request.to_api_dict(),
        )
        r.raise_for_status()
        return TimeEntry.model_validate(r.json())

    def stop_timer(
        self,
        workspace_id: str,
        user_id: str,
        request: StopTimerRequest,
    ) -> TimeEntry:
        """Stop the currently running timer."""
        r = self._client.patch(
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            json={"end": request.end},
        )
        r.raise_for_status()
        return TimeEntry.model_validate(r.json())

    def delete_time_entry(self, workspace_id: str, entry_id: str) -> None:
        """Delete a time entry."""
        r = self._client.delete(f"/workspaces/{workspace_id}/time-entries/{entry_id}")
        r.raise_for_status()

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> ClockifyAPI:
        """Context manager entry."""
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit."""
        self.close()
