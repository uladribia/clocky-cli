"""Tests for runtime smoke-case selection.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import clocky.integration_smoke as integration_smoke
from clocky.integration_smoke import CaseResult, resolve_missing_tag_project, run_cases
from clocky.smoke_planner import RepresentativeCommand, SmokePlan


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    """Create a completed-process test double."""
    return subprocess.CompletedProcess(
        args=["clocky"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_resolve_missing_tag_project_prefers_candidate_that_still_fails(
    monkeypatch,
) -> None:
    plan = SmokePlan(
        start_stop_project="Cross-selling",
        missing_tag_project="Brokerages",
        representatives={
            "missing_tag": [
                RepresentativeCommand(
                    case_name="missing_tag",
                    command='clocky start --non-interactive "Latte"',
                    project_name="Latte",
                    source_path=Path("logs/launcher.log"),
                ),
                RepresentativeCommand(
                    case_name="missing_tag",
                    command='clocky start --non-interactive "Brokerages"',
                    project_name="Brokerages",
                    source_path=Path("logs/launcher.log"),
                ),
            ]
        },
    )
    seen: list[list[str]] = []

    def fake_run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
        seen.append(args)
        if args[-1] == "Latte":
            return _proc(0, stdout="{}\n")
        return _proc(1, stderr="CLOCKY_ERROR_MISSING_TAG_MAP\n")

    monkeypatch.setattr(integration_smoke, "run_cli", fake_run_cli)

    assert resolve_missing_tag_project(plan) == "Brokerages"
    assert seen[0][-1] == "Latte"
    assert seen[1][-1] == "Brokerages"
    assert all("--dry-run" in call for call in seen)


def test_run_cases_reports_clear_failure_when_no_missing_tag_candidate(monkeypatch) -> None:
    plan = SmokePlan(
        start_stop_project="Cross-selling",
        missing_tag_project="Brokerages",
        representatives={
            "missing_tag": [
                RepresentativeCommand(
                    case_name="missing_tag",
                    command='clocky start --non-interactive "Latte"',
                    project_name="Latte",
                    source_path=Path("logs/launcher.log"),
                )
            ]
        },
    )

    monkeypatch.setattr(integration_smoke, "run_cli", lambda _args: _proc(0, stdout="{}\n"))

    results = run_cases(["missing_tag"], plan)

    assert results == [
        CaseResult(
            name="missing_tag",
            success=False,
            details="No valid missing-tag smoke candidate found. Checked: Latte, Brokerages",
        )
    ]
