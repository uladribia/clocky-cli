"""Tests for smoke planning based on usage logs.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path

from clocky.smoke_planner import (
    DEFAULT_MISSING_TAG_PROJECT,
    DEFAULT_START_STOP_PROJECT,
    build_smoke_plan,
    collect_representative_commands,
    discover_usage_logs,
    smoke_plan_to_dict,
)


def test_discover_usage_logs_returns_existing_paths(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    launcher_log = logs_dir / "launcher.log"
    launcher_log.write_text("launcher=start\n", encoding="utf-8")

    paths = discover_usage_logs(tmp_path)

    assert paths == [launcher_log]


def test_collect_representative_commands_parses_launcher_patterns(tmp_path: Path) -> None:
    log_path = tmp_path / "launcher.log"
    log_path.write_text(
        "\n".join(
            [
                "2026-03-29T10:00:00Z query=Cros-seling",
                "2026-03-29T10:00:01Z clocky start output: Project: Cross-selling",
                "2026-03-29T10:01:00Z query=hoke",
                "2026-03-29T10:01:01Z clocky start failed: Project: Brokerages",
                (
                    "2026-03-29T10:01:02Z ✘ No tag mapping found for 'Brokerages'. "
                    "Run interactively once with --tag."
                ),
                "RUN: clocky list --limit 5",
                "RUN: clocky --json status",
            ]
        ),
        encoding="utf-8",
    )

    commands = collect_representative_commands([log_path])

    assert commands["start_stop"][0].project_name == "Cross-selling"
    assert commands["missing_tag"][0].project_name == "Brokerages"
    assert commands["list_entries"][0].command == "clocky list --limit 5"
    assert commands["status_json"][0].command == "clocky --json status"


def test_build_smoke_plan_uses_log_projects_when_available(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "launcher.log").write_text(
        "\n".join(
            [
                "2026-03-29T10:00:00Z query=Cros-seling",
                "2026-03-29T10:00:01Z clocky start output: Project: Cross-selling",
                "2026-03-29T10:01:00Z query=hoke",
                (
                    "2026-03-29T10:01:01Z ✘ No tag mapping found for 'Brokerages'. "
                    "Run interactively once with --tag."
                ),
            ]
        ),
        encoding="utf-8",
    )

    plan = build_smoke_plan(tmp_path)

    assert plan.start_stop_project == "Cross-selling"
    assert plan.missing_tag_project == "Brokerages"
    assert "start_stop" not in plan.fallback_cases
    assert "missing_tag" not in plan.fallback_cases


def test_build_smoke_plan_falls_back_without_logs(tmp_path: Path) -> None:
    plan = build_smoke_plan(tmp_path)

    assert plan.start_stop_project == DEFAULT_START_STOP_PROJECT
    assert plan.missing_tag_project == DEFAULT_MISSING_TAG_PROJECT
    assert "start_stop" in plan.fallback_cases
    assert "missing_tag" in plan.fallback_cases
    assert plan.representatives["list_entries"][0].command == "clocky list --limit 5"


def test_smoke_plan_to_dict_returns_json_safe_payload(tmp_path: Path) -> None:
    plan = build_smoke_plan(tmp_path)

    payload = smoke_plan_to_dict(plan)

    assert payload["start_stop_project"] == DEFAULT_START_STOP_PROJECT
    assert payload["missing_tag_project"] == DEFAULT_MISSING_TAG_PROJECT
    assert isinstance(payload["representatives"], dict)
