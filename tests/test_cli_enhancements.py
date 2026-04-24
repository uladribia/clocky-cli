"""Tests for CLI enhancements: --json, --quiet, --dry-run, --force, delete, NO_COLOR.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import clocky.cli.main as cli
from clocky.domain.models import Project
from clocky.infra.api import ClockifyAPIError
from clocky.infra.context import AppContext
from clocky.infra.smoke_planner import RepresentativeCommand, SmokePlan
from clocky.testing import MOCK_PROJECTS, MOCK_TIME_ENTRIES, MockClockifyAPI


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def ctx() -> AppContext:
    api = MockClockifyAPI()
    user = api.get_user()
    return AppContext(api=api, user=user, workspace_id=user.default_workspace)


@pytest.fixture
def ctx_with_timer() -> AppContext:
    api = MockClockifyAPI(running_timer=MOCK_TIME_ENTRIES[0])
    user = api.get_user()
    return AppContext(api=api, user=user, workspace_id=user.default_workspace)


class TestJsonOutput:
    def test_status_json_no_timer(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--json", "status"])
        assert result.exit_code == 0
        assert json.loads(result.output) is None

    def test_status_json_with_timer(
        self, runner: CliRunner, ctx_with_timer: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx_with_timer)
        result = runner.invoke(cli.app, ["--json", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "entry-001"
        assert data["project_name"] == "Website Redesign"

    def test_list_json(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--json", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_projects_json_no_client(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--json", "projects"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 5

    def test_projects_json_excludes_archived(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        api = MockClockifyAPI(
            projects=[
                *MOCK_PROJECTS,
                Project(
                    id="proj-archived",
                    name="Archived Redesign",
                    client_id="cli-001",
                    client_name="Acme Corp",
                    archived=True,
                ),
            ]
        )
        user = api.get_user()
        ctx = AppContext(api=api, user=user, workspace_id=user.default_workspace)
        monkeypatch.setattr(cli, "build_context", lambda: ctx)

        result = runner.invoke(cli.app, ["--json", "projects"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert {project["id"] for project in data} == {project.id for project in MOCK_PROJECTS}
        assert all(project["archived"] is False for project in data)

    def test_start_json(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--json", "start", "Website", "--non-interactive"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "entry-new"

    def test_stop_json_no_timer(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--json", "stop"])
        assert result.exit_code == 0
        assert json.loads(result.output) is None

    def test_delete_json(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--json", "delete", "entry-001", "--force"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["deleted"] == "entry-001"


class TestQuietOutput:
    def test_quiet_start_minimal(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["--quiet", "start", "Website", "--non-interactive"])
        assert result.exit_code == 0
        # Should still have success message but no tag/project info lines
        assert "Timer started" in result.output
        assert "Project:" not in result.output


class TestDryRun:
    def test_dry_run_does_not_start(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["start", "Website", "--non-interactive", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        # No timer should be running
        assert ctx.api.get_running_timer("ws-001", "user-001") is None

    def test_dry_run_json(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(
            cli.app, ["--json", "start", "Website", "--non-interactive", "--dry-run"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert "Website Redesign" in data["project"]


class TestDeleteCommand:
    def test_delete_with_force(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["delete", "entry-001", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_requires_entry_id(self, runner: CliRunner) -> None:
        result = runner.invoke(cli.app, ["delete"])
        assert result.exit_code != 0


class TestProjectsOptionalClient:
    def test_projects_all(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["projects"])
        assert result.exit_code == 0
        assert "Projects" in result.output

    def test_projects_with_client(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["projects", "Acme"])
        assert result.exit_code == 0
        assert "Projects" in result.output


class TestExitCodes:
    def test_no_match_returns_2(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        result = runner.invoke(cli.app, ["start", "zzzznonexistent", "--non-interactive"])
        assert result.exit_code == 2

    def test_start_timeout_is_graceful(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            "clocky.infra.query_cache._cache_path",
            lambda: tmp_path / "query-cache.json",
        )
        api = MockClockifyAPI(
            fail_get_time_entries=ClockifyAPIError(
                "Clockify API timed out after 3 attempts. Please try again."
            )
        )
        user = api.get_user()
        ctx = AppContext(api=api, user=user, workspace_id=user.default_workspace)
        monkeypatch.setattr(cli, "build_context", lambda: ctx)

        result = runner.invoke(cli.app, ["start", "Website", "--non-interactive"])

        assert result.exit_code == 1
        assert "Clockify API timed out after 3 attempts" in result.output
        assert "Traceback" not in result.output


class TestIntegrationPlan:
    def test_integration_test_plan_json(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan = SmokePlan(
            start_stop_project="Cross-selling",
            missing_tag_project="Brokerages",
            representatives={
                "start_stop": [
                    RepresentativeCommand(
                        case_name="start_stop",
                        command='clocky start --non-interactive "Cros-seling"',
                        project_name="Cross-selling",
                        source_path=Path("logs/launcher.log"),
                    )
                ]
            },
            fallback_cases=(),
            log_paths=(Path("logs/launcher.log"),),
        )
        monkeypatch.setattr(cli, "build_smoke_plan", lambda: plan)
        result = runner.invoke(cli.app, ["--json", "integration-test", "--plan"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["start_stop_project"] == "Cross-selling"
        assert data["missing_tag_project"] == "Brokerages"


class TestNoColor:
    def test_no_color_env(
        self, runner: CliRunner, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cli, "build_context", lambda: ctx)
        monkeypatch.setenv("NO_COLOR", "1")
        result = runner.invoke(cli.app, ["status"])
        assert result.exit_code == 0
        # Should not contain ANSI escape codes
        assert "\x1b[" not in result.output
