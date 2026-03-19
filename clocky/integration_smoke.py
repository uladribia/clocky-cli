# SPDX-License-Identifier: MIT
"""Real integration smoke tests for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from clocky.context import build_context
from clocky.tag_map import TagMap

DEFAULT_HISTORY_LIMIT = 100
DEFAULT_LIST_LIMIT = 5
DEFAULT_CASES = ("start_stop", "missing_tag", "list_entries", "status_json")


@dataclass(frozen=True)
class CaseResult:
    """Result of a single test case."""

    name: str
    success: bool
    details: str = ""


@dataclass(frozen=True)
class ProjectSelection:
    """Resolved project names for test cases."""

    start_stop_project: str
    missing_tag_project: str


def cli_base_command() -> list[str]:
    """Return the base CLI command to execute.

    Uses CLOCKY_INTEGRATION_CLI when provided; defaults to ``uv run clocky``.
    """
    command = os.environ.get("CLOCKY_INTEGRATION_CLI", "uv run clocky")
    return shlex.split(command)


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the clocky CLI with the provided arguments.

    Args:
        args: CLI arguments (excluding the base command).

    Returns:
        Completed process with stdout/stderr captured.

    """
    command = cli_base_command() + args
    return subprocess.run(  # noqa: S603
        command,
        text=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def latest_project_candidates(entries: Iterable[object]) -> list[str]:
    """Return unique project IDs in most-recent-first order.

    Args:
        entries: TimeEntry objects from the API.

    Returns:
        List of project IDs ordered by first appearance.

    """
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in entries:
        project_id = getattr(entry, "project_id", None)
        if not project_id or project_id in seen:
            continue
        seen.add(project_id)
        ordered.append(project_id)
    return ordered


def select_projects(history_limit: int) -> ProjectSelection:
    """Select projects for smoke tests using recent usage.

    Args:
        history_limit: Number of recent entries to inspect.

    Returns:
        Selected project names for each test case.

    Raises:
        RuntimeError: When no suitable projects are found.

    """
    env_start_project = os.environ.get("CLOCKY_TEST_PROJECT")
    env_missing_tag_project = os.environ.get("CLOCKY_TEST_PROJECT_MISSING_TAG")
    if env_start_project and env_missing_tag_project:
        return ProjectSelection(
            start_stop_project=env_start_project,
            missing_tag_project=env_missing_tag_project,
        )

    ctx = build_context()
    try:
        projects = {p.id: p for p in ctx.api.get_projects(ctx.workspace_id)}
        entries = ctx.api.get_time_entries(
            ctx.workspace_id,
            ctx.user.id,
            limit=history_limit,
        )
    finally:
        ctx.api.close()

    if not entries:
        raise RuntimeError(
            "No recent entries found. Set CLOCKY_TEST_PROJECT and "
            "CLOCKY_TEST_PROJECT_MISSING_TAG to run integration tests."
        )

    tag_map = TagMap.load().project_to_tag
    projects_with_recent_tags = {
        entry.project_id for entry in entries if entry.project_id and entry.tag_ids
    }

    ordered_project_ids = latest_project_candidates(entries)

    def is_usable(project_id: str) -> bool:
        project = projects.get(project_id)
        return bool(project) and not project.archived

    start_stop_project: str | None = env_start_project
    if start_stop_project is None:
        for project_id in ordered_project_ids:
            if not is_usable(project_id):
                continue
            if project_id in tag_map or project_id in projects_with_recent_tags:
                start_stop_project = projects[project_id].name
                break

    missing_tag_project: str | None = env_missing_tag_project
    if missing_tag_project is None:
        for project_id in ordered_project_ids:
            if not is_usable(project_id):
                continue
            if project_id in tag_map or project_id in projects_with_recent_tags:
                continue
            missing_tag_project = projects[project_id].name
            break

    if not start_stop_project:
        raise RuntimeError(
            "No suitable project found for start/stop smoke test. "
            "Set CLOCKY_TEST_PROJECT to override selection."
        )
    if not missing_tag_project:
        raise RuntimeError(
            "No suitable project found for missing-tag smoke test. "
            "Set CLOCKY_TEST_PROJECT_MISSING_TAG to override selection."
        )

    return ProjectSelection(
        start_stop_project=start_stop_project,
        missing_tag_project=missing_tag_project,
    )


def assert_contains(text: str, needle: str, case: str) -> None:
    """Assert that a substring exists in text.

    Args:
        text: Text to search.
        needle: Required substring.
        case: Case name for error messages.

    Raises:
        AssertionError: When ``needle`` is missing.

    """
    if needle not in text:
        raise AssertionError(f"{case}: expected '{needle}' in output")


def case_start_stop(project_name: str) -> CaseResult:
    """Run start/status/stop smoke test."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    description = f"[ITEST] start-stop {timestamp}"

    start_proc = run_cli(
        [
            "start",
            "--non-interactive",
            project_name,
            "--description",
            description,
        ]
    )
    if start_proc.returncode != 0:
        return CaseResult(
            name="start_stop",
            success=False,
            details=f"start failed: {start_proc.stderr.strip()}",
        )

    status_proc = run_cli(["status"])
    stop_proc = run_cli(["stop", "--force"])

    try:
        assert_contains(start_proc.stdout, "Timer started", "start_stop")
        assert_contains(status_proc.stdout, "Timer running", "start_stop")
        assert_contains(stop_proc.stdout, "Timer stopped", "start_stop")
    except AssertionError as exc:
        return CaseResult(name="start_stop", success=False, details=str(exc))

    return CaseResult(name="start_stop", success=True)


def case_missing_tag(project_name: str) -> CaseResult:
    """Run missing-tag sentinel test."""
    proc = run_cli(["start", "--non-interactive", project_name])
    try:
        if proc.returncode == 0:
            raise AssertionError("missing_tag: expected non-zero exit code")
        assert_contains(proc.stderr, "CLOCKY_ERROR_MISSING_TAG_MAP", "missing_tag")
    except AssertionError as exc:
        return CaseResult(name="missing_tag", success=False, details=str(exc))

    return CaseResult(name="missing_tag", success=True)


def case_list_entries() -> CaseResult:
    """Run list entries smoke test."""
    proc = run_cli(["list", "--limit", str(DEFAULT_LIST_LIMIT)])
    try:
        if proc.returncode != 0:
            raise AssertionError(f"list_entries: exit code {proc.returncode}")
        assert_contains(proc.stdout, "Recent Time Entries", "list_entries")
    except AssertionError as exc:
        return CaseResult(name="list_entries", success=False, details=str(exc))

    return CaseResult(name="list_entries", success=True)


def case_status_json() -> CaseResult:
    """Run JSON status smoke test."""
    proc = run_cli(["--json", "status"])
    try:
        if proc.returncode != 0:
            raise AssertionError(f"status_json: exit code {proc.returncode}")
        json.loads(proc.stdout)
    except (AssertionError, json.JSONDecodeError) as exc:
        return CaseResult(name="status_json", success=False, details=str(exc))

    return CaseResult(name="status_json", success=True)


def run_cases(cases: list[str], history_limit: int) -> list[CaseResult]:
    """Run the requested integration cases.

    Args:
        cases: Case names to run.
        history_limit: Time entry history limit for project selection.

    Returns:
        List of case results.

    """
    selection: ProjectSelection | None = None
    results: list[CaseResult] = []

    for case in cases:
        if case in {"start_stop", "missing_tag"} and selection is None:
            selection = select_projects(history_limit)

        if case == "start_stop":
            assert selection is not None
            results.append(case_start_stop(selection.start_stop_project))
        elif case == "missing_tag":
            assert selection is not None
            results.append(case_missing_tag(selection.missing_tag_project))
        elif case == "list_entries":
            results.append(case_list_entries())
        elif case == "status_json":
            results.append(case_status_json())

    return results


def report_results(results: list[CaseResult]) -> int:
    """Report results to stdout and return exit code.

    Args:
        results: Completed case results.

    Returns:
        Exit code (0 when all passed, 1 otherwise).

    """
    failed = [result for result in results if not result.success]
    for result in results:
        status = "PASS" if result.success else "FAIL"
        details = f" - {result.details}" if result.details else ""
        sys.stdout.write(f"{status}: {result.name}{details}\n")

    return 1 if failed else 0


def run_integration_smoke(cases: list[str], history_limit: int) -> int:
    """Run integration smoke tests and return exit code.

    Args:
        cases: Case names to execute.
        history_limit: Time entry history limit for project selection.

    Returns:
        Exit code suitable for CLI usage.

    """
    results = run_cases(cases, history_limit)
    return report_results(results)
