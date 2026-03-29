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
from dataclasses import dataclass
from datetime import UTC, datetime

from clocky.smoke_planner import (
    DEFAULT_MISSING_TAG_PROJECT,
    SmokePlan,
    build_smoke_plan,
    smoke_plan_to_dict,
    smoke_plan_to_lines,
)

DEFAULT_HISTORY_LIMIT = 100
DEFAULT_LIST_LIMIT = 5
DEFAULT_CASES = ("start_stop", "missing_tag", "list_entries", "status_json")


@dataclass(frozen=True)
class CaseResult:
    """Result of a single test case."""

    name: str
    success: bool
    details: str = ""


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
    """Run start/status/stop smoke test with cleanup."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    description = f"[ITEST] start-stop {timestamp}"
    cleanup_errors: list[str] = []

    start_proc = run_cli(
        [
            "--json",
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

    try:
        start_payload = json.loads(start_proc.stdout)
        entry_id = start_payload.get("id")
        if not entry_id:
            raise ValueError("Missing entry id")
    except (json.JSONDecodeError, ValueError) as exc:
        return CaseResult(name="start_stop", success=False, details=f"start JSON: {exc}")

    status_proc = run_cli(["status"])
    stop_proc = run_cli(["stop", "--force"])

    delete_proc = run_cli(["delete", entry_id, "--force"])
    if delete_proc.returncode != 0:
        cleanup_errors.append(delete_proc.stderr.strip() or "delete failed")

    try:
        assert_contains(status_proc.stdout, "Timer running", "start_stop")
        assert_contains(stop_proc.stdout, "Timer stopped", "start_stop")
    except AssertionError as exc:
        cleanup_note = f"; cleanup: {', '.join(cleanup_errors)}" if cleanup_errors else ""
        return CaseResult(name="start_stop", success=False, details=f"{exc}{cleanup_note}")

    if cleanup_errors:
        return CaseResult(
            name="start_stop",
            success=False,
            details=f"cleanup failed: {', '.join(cleanup_errors)}",
        )

    return CaseResult(name="start_stop", success=True)


def _missing_tag_candidates(plan: SmokePlan) -> list[str]:
    """Return candidate project names for the missing-tag smoke case."""
    candidates = [
        *(command.project_name for command in plan.representatives.get("missing_tag", [])),
        plan.missing_tag_project,
        DEFAULT_MISSING_TAG_PROJECT,
    ]
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


def resolve_missing_tag_project(plan: SmokePlan) -> str | None:
    """Probe candidate projects and return one that still triggers the sentinel.

    The probe uses ``start --dry-run`` to avoid mutating real Clockify state.
    """
    for project_name in _missing_tag_candidates(plan):
        proc = run_cli(["start", "--non-interactive", "--dry-run", project_name])
        if proc.returncode != 0 and "CLOCKY_ERROR_MISSING_TAG_MAP" in proc.stderr:
            return project_name
    return None


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


def run_cases(cases: list[str], plan: SmokePlan) -> list[CaseResult]:
    """Run the requested integration cases.

    Args:
        cases: Case names to run.
        plan: Selected smoke plan.

    Returns:
        List of case results.

    """
    results: list[CaseResult] = []

    for case in cases:
        if case == "start_stop":
            results.append(case_start_stop(plan.start_stop_project))
        elif case == "missing_tag":
            project_name = resolve_missing_tag_project(plan)
            if project_name is None:
                checked = ", ".join(_missing_tag_candidates(plan)) or "<none>"
                results.append(
                    CaseResult(
                        name="missing_tag",
                        success=False,
                        details=(f"No valid missing-tag smoke candidate found. Checked: {checked}"),
                    )
                )
            else:
                results.append(case_missing_tag(project_name))
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


def render_smoke_plan(plan: SmokePlan) -> str:
    """Return a readable smoke plan summary."""
    return "\n".join(smoke_plan_to_lines(plan)) + "\n"


def run_integration_smoke(cases: list[str], history_limit: int) -> int:
    """Run integration smoke tests and return exit code.

    Args:
        cases: Case names to execute.
        history_limit: Kept for CLI compatibility; planning is log-driven.

    Returns:
        Exit code suitable for CLI usage.

    """
    del history_limit
    plan = build_smoke_plan()
    results = run_cases(cases, plan)
    return report_results(results)


__all__ = [
    "CaseResult",
    "DEFAULT_CASES",
    "DEFAULT_HISTORY_LIMIT",
    "DEFAULT_LIST_LIMIT",
    "build_smoke_plan",
    "render_smoke_plan",
    "run_integration_smoke",
    "smoke_plan_to_dict",
]
