"""Tests for Pydantic models."""

from __future__ import annotations

from clocky.models import Project, StartTimerRequest, TimeEntry, User


class TestUser:
    """Tests for User model."""

    def test_valid(self) -> None:
        user = User.model_validate(
            {
                "id": "u1",
                "name": "Alice",
                "email": "a@example.com",
                "defaultWorkspace": "ws-1",
            }
        )
        assert user.id == "u1"
        assert user.default_workspace == "ws-1"

    def test_alias(self) -> None:
        user = User.model_validate(
            {
                "id": "u2",
                "name": "Bob",
                "email": "b@example.com",
                "defaultWorkspace": "ws-2",
            }
        )
        assert user.default_workspace == "ws-2"


class TestProject:
    """Tests for Project model."""

    def test_with_client(self) -> None:
        project = Project.model_validate(
            {
                "id": "p1",
                "name": "My Project",
                "clientId": "c1",
                "clientName": "ACME",
            }
        )
        assert project.client_id == "c1"
        assert project.client_name == "ACME"

    def test_without_client(self) -> None:
        project = Project.model_validate({"id": "p2", "name": "Internal"})
        assert project.client_id is None
        assert project.client_name is None

    def test_archived_default(self) -> None:
        project = Project.model_validate({"id": "p3", "name": "Active"})
        assert project.archived is False


class TestTimeEntry:
    """Tests for TimeEntry model."""

    def test_full_entry(self) -> None:
        entry = TimeEntry.model_validate(
            {
                "id": "e1",
                "description": "Work",
                "projectId": "p1",
                "workspaceId": "ws1",
                "userId": "u1",
                "tagIds": ["t1"],
                "timeInterval": {
                    "start": "2024-01-01T09:00:00Z",
                    "end": "2024-01-01T10:00:00Z",
                    "duration": "PT1H",
                },
            }
        )
        assert entry.id == "e1"
        assert entry.time_interval.duration == "PT1H"

    def test_running_no_end(self) -> None:
        entry = TimeEntry.model_validate(
            {
                "id": "e2",
                "workspaceId": "ws1",
                "userId": "u1",
                "tagIds": [],
                "timeInterval": {"start": "2024-01-01T09:00:00Z"},
            }
        )
        assert entry.time_interval.end is None

    def test_description_default(self) -> None:
        entry = TimeEntry.model_validate(
            {
                "id": "e3",
                "workspaceId": "ws1",
                "userId": "u1",
                "tagIds": [],
                "timeInterval": {"start": "2024-01-01T09:00:00Z"},
            }
        )
        assert entry.description == ""


class TestStartTimerRequest:
    """Tests for StartTimerRequest serialization."""

    def test_to_api_dict_with_project(self) -> None:
        req = StartTimerRequest(
            start="2024-01-01T09:00:00Z",
            description="hello",
            project_id="proj-1",
        )
        d = req.to_api_dict()
        assert d["projectId"] == "proj-1"
        assert d["description"] == "hello"

    def test_to_api_dict_no_project(self) -> None:
        req = StartTimerRequest(start="2024-01-01T09:00:00Z")
        d = req.to_api_dict()
        assert d.get("projectId") is None

    def test_to_api_dict_with_tags(self) -> None:
        req = StartTimerRequest(start="2024-01-01T09:00:00Z", tag_ids=["t1", "t2"])
        d = req.to_api_dict()
        assert d["tagIds"] == ["t1", "t2"]

    def test_to_api_dict_no_tags(self) -> None:
        req = StartTimerRequest(start="2024-01-01T09:00:00Z")
        d = req.to_api_dict()
        assert d["tagIds"] == []
