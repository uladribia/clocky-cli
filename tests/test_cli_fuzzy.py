# SPDX-License-Identifier: MIT
"""Tests for CLI fuzzy matching logic.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from typer.testing import CliRunner

import clocky.cli as cli
import clocky.cli_helpers.selection as selection
from clocky.context import AppContext
from clocky.fuzzy import fuzzy_search_projects
from clocky.models import Project, Tag, TimeEntry
from clocky.testing import MOCK_CLIENTS, MockClockifyAPI


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def ctx_with_projects() -> AppContext:
    projects = [
        Project(
            id="proj-guess-2025",
            name="Guess Manteniment 2025",
            client_id=MOCK_CLIENTS[0].id,
            client_name=MOCK_CLIENTS[0].name,
            archived=False,
        ),
        Project(
            id="proj-guess-2024",
            name="Guess Manteniment 2024",
            client_id=MOCK_CLIENTS[0].id,
            client_name=MOCK_CLIENTS[0].name,
            archived=False,
        ),
        Project(
            id="proj-guess-2026",
            name="Guess Manteniment 2026",
            client_id=MOCK_CLIENTS[0].id,
            client_name=MOCK_CLIENTS[0].name,
            archived=False,
        ),
    ]
    tags = [
        Tag(id="tag-acman", name="AccMan", workspaceId="ws-001"),
        Tag(id="tag-admin", name="Admin", workspaceId="ws-001"),
    ]
    entries = [
        TimeEntry.model_validate(
            {
                "id": "entry-2025-1",
                "description": "Recent work",
                "projectId": "proj-guess-2025",
                "workspaceId": "ws-001",
                "userId": "user-001",
                "tagIds": ["tag-admin"],
                "timeInterval": {
                    "start": "2026-03-28T09:00:00Z",
                    "end": "2026-03-28T10:00:00Z",
                    "duration": "PT1H",
                },
            }
        ),
        TimeEntry.model_validate(
            {
                "id": "entry-2025-2",
                "description": "More recent work",
                "projectId": "proj-guess-2025",
                "workspaceId": "ws-001",
                "userId": "user-001",
                "tagIds": ["tag-admin"],
                "timeInterval": {
                    "start": "2026-03-27T09:00:00Z",
                    "end": "2026-03-27T10:00:00Z",
                    "duration": "PT1H",
                },
            }
        ),
        TimeEntry.model_validate(
            {
                "id": "entry-2026-1",
                "description": "Target project",
                "projectId": "proj-guess-2026",
                "workspaceId": "ws-001",
                "userId": "user-001",
                "tagIds": ["tag-acman"],
                "timeInterval": {
                    "start": "2026-03-20T09:00:00Z",
                    "end": "2026-03-20T10:00:00Z",
                    "duration": "PT1H",
                },
            }
        ),
    ]

    api = MockClockifyAPI(projects=projects, tags=tags, time_entries=entries)
    user = api.get_user()
    return AppContext(api=api, user=user, workspace_id=user.default_workspace)


def test_start_non_interactive_uses_weighted_top_match(
    runner: CliRunner, ctx_with_projects: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-interactive mode should auto-pick the top-ranked weighted match."""
    monkeypatch.setattr(cli, "build_context", lambda: ctx_with_projects)

    result = runner.invoke(
        cli.app,
        ["start", "Guess manteniments 2026", "--non-interactive", "--tag", "acc"],
    )

    assert result.exit_code == 0
    assert "Project: Guess Manteniment 2026" in result.stdout
    assert "Tag (explicit): AccMan" in result.stdout


def test_pick_one_uses_same_ranked_matches_in_both_modes(
    ctx_with_projects: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive and non-interactive selection should use the same ordering."""
    matches = fuzzy_search_projects(
        "Guess",
        ctx_with_projects.api.get_projects(ctx_with_projects.workspace_id),
        ctx_with_projects.api.get_time_entries(
            ctx_with_projects.workspace_id, ctx_with_projects.user.id
        ),
    )

    chosen_values: list[Project] = []

    class _Select:
        def __init__(self, value: object) -> None:
            self._value = value

        def ask(self) -> object:
            return self._value

    def _mock_select(*_args: object, **kwargs: Any) -> _Select:
        choices = cast(list[Any], kwargs["choices"])
        chosen_project = cast(Project, choices[0].value)
        chosen_values.append(chosen_project)
        return _Select(chosen_project)

    monkeypatch.setattr(selection.questionary, "select", _mock_select)
    monkeypatch.setattr(selection.sys.stdin, "isatty", lambda: True)

    interactive = selection.pick_one(matches, "name")
    non_interactive = selection.pick_one(matches, "name", non_interactive=True)

    assert chosen_values
    assert chosen_values[0].name == "Guess Manteniment 2025"
    assert interactive is not None
    assert non_interactive is not None
    assert interactive.name == "Guess Manteniment 2025"
    assert non_interactive.name == "Guess Manteniment 2025"
