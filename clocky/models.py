"""Pydantic models for Clockify API data structures.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """Clockify user."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    email: str
    default_workspace: str = Field(alias="defaultWorkspace")


class Workspace(BaseModel):
    """Clockify workspace."""

    id: str
    name: str


class Client(BaseModel):
    """Clockify client."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    workspace_id: str = Field(alias="workspaceId")


class Project(BaseModel):
    """Clockify project."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    client_id: str | None = Field(default=None, alias="clientId")
    client_name: str | None = Field(default=None, alias="clientName")
    archived: bool = False


class TimeInterval(BaseModel):
    """Time interval of a time entry."""

    start: datetime
    end: datetime | None = None
    duration: str | None = None


class TimeEntry(BaseModel):
    """Clockify time entry."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    description: str = ""
    project_id: str | None = Field(default=None, alias="projectId")
    workspace_id: str = Field(alias="workspaceId")
    user_id: str = Field(alias="userId")
    time_interval: TimeInterval = Field(alias="timeInterval")
    tag_ids: list[str] = Field(default_factory=list, alias="tagIds")


class Tag(BaseModel):
    """Clockify tag."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    workspace_id: str = Field(alias="workspaceId")


class StartTimerRequest(BaseModel):
    """Request body for starting a new time entry."""

    start: str
    description: str = ""
    project_id: str | None = Field(default=None, serialization_alias="projectId")
    tag_ids: list[str] = Field(default_factory=list, serialization_alias="tagIds")

    def to_api_dict(self) -> dict[str, object]:
        """Serialize to the dict format expected by the Clockify API."""
        return self.model_dump(by_alias=True, exclude_none=True)


class StopTimerRequest(BaseModel):
    """Request body for stopping a running time entry."""

    end: str
