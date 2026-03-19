# SPDX-License-Identifier: MIT
"""Tests for CLI fuzzy matching logic.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

import clocky.cli as cli
from clocky.context import AppContext
from clocky.models import Project, Tag
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
            id="proj-alpha",
            name="Project Alpha",
            client_id=MOCK_CLIENTS[0].id,
            client_name=MOCK_CLIENTS[0].name,
            archived=False,
        ),
        Project(
            id="proj-beta",
            name="Project Beta",
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
        ),  # Add the intended project
    ]
    tags = [
        Tag(id="tag-acman", name="AccMan", workspaceId="ws-001"),
        Tag(id="tag-comercial", name="Comercial", workspaceId="ws-001"),
    ]

    api = MockClockifyAPI(projects=projects, tags=tags)
    user = api.get_user()
    return AppContext(api=api, user=user, workspace_id=user.default_workspace)


def test_start_non_interactive_no_high_confidence_match_fails(
    runner: CliRunner, ctx_with_projects: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-interactive start with no high-confidence fuzzy match should fail."""
    monkeypatch.setattr(cli, "build_context", lambda: ctx_with_projects)
    import clocky.fuzzy as fuzzy_module

    monkeypatch.setattr(fuzzy_module, "DEFAULT_CUTOFF", 70)
    monkeypatch.setattr(
        fuzzy_module, "FUZZY_NON_INTERACTIVE_THRESHOLD", 95
    )  # Set below 100 for this test

    result = runner.invoke(cli.app, ["start", "Guess manteniments 2026", "--non-interactive"])

    assert result.exit_code == 2

    # Normalize stderr: remove Rich styling, multiple newlines/spaces, and "✘"
    normalized_stderr = (
        result.stderr.replace("\n", " ")
        .replace("✘ ", "")  # Remove the Rich error symbol
        .strip()
    )
    # Replace multiple spaces with a single space
    normalized_stderr = re.sub(r"\s+", " ", normalized_stderr)

    expected_msg_start = "No exact project match found in non-interactive mode."
    expected_msg_middle_pattern = r"Closest match was 'Guess Manteniment 2026' \(score: \d+%\)\."
    expected_msg_end = "Please use a more precise query or interactive mode."

    assert expected_msg_start in normalized_stderr
    assert re.search(expected_msg_middle_pattern, normalized_stderr) is not None
    assert expected_msg_end in normalized_stderr


def test_start_non_interactive_with_exact_match_succeeds(
    runner: CliRunner, ctx_with_projects: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-interactive start with a 100% fuzzy match should succeed."""
    monkeypatch.setattr(cli, "build_context", lambda: ctx_with_projects)
    import clocky.fuzzy as fuzzy_module

    monkeypatch.setattr(fuzzy_module, "DEFAULT_CUTOFF", 70)
    monkeypatch.setattr(
        fuzzy_module, "FUZZY_NON_INTERACTIVE_THRESHOLD", 100
    )  # Require 100% for this test

    # Simulate a 100% match for "Guess Manteniment 2026"
    result = runner.invoke(
        cli.app, ["start", "Guess Manteniment 2026", "--non-interactive", "--tag", "AccMan"]
    )

    assert result.exit_code == 0
    assert "Timer started" in result.stdout
    assert "Project: Guess Manteniment 2026" in result.stdout
    assert "Tag (explicit): AccMan" in result.stdout
