"""Tests for main CLI flows (start/stop/list/projects).

SPDX-License-Identifier: MIT

These tests monkeypatch the CLI context builder so commands run fully offline
using the MockClockifyAPI.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

import clocky.cli as cli
from clocky.context import AppContext
from clocky.testing import MockClockifyAPI


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def ctx() -> AppContext:
    api = MockClockifyAPI()
    user = api.get_user()
    return AppContext(api=api, user=user, workspace_id=user.default_workspace)


def test_status_no_timer(
    runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "build_context", lambda: ctx)
    result = runner.invoke(cli.app, ["status"])
    assert result.exit_code == 0
    assert "No timer" in result.output


def test_start_non_interactive_sets_project(
    runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "build_context", lambda: ctx)
    result = runner.invoke(cli.app, ["start", "Project Alpha", "--non-interactive"])
    assert result.exit_code == 0
    assert "Timer started" in result.output


def test_stop_no_timer_is_noop(
    runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "build_context", lambda: ctx)
    result = runner.invoke(cli.app, ["stop"])
    assert result.exit_code == 0
    assert "No timer" in result.output


def test_list_shows_table(
    runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Add a timer entry
    monkeypatch.setattr(cli, "build_context", lambda: ctx)
    _ = runner.invoke(cli.app, ["start", "Project Alpha", "--non-interactive"])
    _ = runner.invoke(cli.app, ["stop"])

    result = runner.invoke(cli.app, ["list", "--limit", "5"])
    assert result.exit_code == 0
    assert "Recent Time Entries" in result.output


def test_projects_requires_client_arg(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, ["projects"])
    assert result.exit_code != 0


def test_projects_for_client_filters(
    runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "build_context", lambda: ctx)
    result = runner.invoke(cli.app, ["projects", "Acme", "--search", "Alpha"])
    assert result.exit_code == 0
    assert "Projects" in result.output
