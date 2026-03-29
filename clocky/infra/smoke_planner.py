# SPDX-License-Identifier: MIT
"""Planning helpers for real integration smoke tests.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_START_STOP_PROJECT = "Cross-selling"
DEFAULT_MISSING_TAG_PROJECT = "Brokerages"
DEFAULT_LIST_COMMAND = "clocky list --limit 5"
DEFAULT_STATUS_JSON_COMMAND = "clocky --json status"
_DEFAULT_REPRESENTATIVE_LIMIT = 5
_PROJECT_RE = re.compile(r"Project:\s*(?P<name>.+)")
_MISSING_TAG_RE = re.compile(r"No tag mapping found for '(?P<name>[^']+)'")


@dataclass(frozen=True)
class RepresentativeCommand:
    """Representative command observed in usage logs.

    Attributes:
        case_name: Smoke case category.
        command: Human-readable command string.
        project_name: Resolved project name when available.
        source_path: Log file the command came from.

    """

    case_name: str
    command: str
    project_name: str | None
    source_path: Path


@dataclass(frozen=True)
class SmokePlan:
    """Resolved inputs and representative commands for smoke cases."""

    start_stop_project: str
    missing_tag_project: str
    representatives: dict[str, list[RepresentativeCommand]] = field(default_factory=dict)
    fallback_cases: tuple[str, ...] = ()
    log_paths: tuple[Path, ...] = ()


def discover_usage_logs(repo_root: Path | None = None) -> list[Path]:
    """Return available usage logs in preferred order.

    Args:
        repo_root: Repository root. Defaults to the parent of this module.

    Returns:
        Existing log paths ordered from most specific to most general.

    """
    root = repo_root or Path(__file__).resolve().parent.parent
    candidates = [
        root / "logs" / "integration-launcher.log",
        root / "logs" / "launcher.log",
    ]
    if repo_root is None:
        candidates.append(Path.home() / ".local" / "state" / "clocky" / "launcher.log")
    return [path for path in candidates if path.exists()]


def _extract_project_name(text: str) -> str | None:
    """Extract a project name from free-form command output."""
    match = _PROJECT_RE.search(text)
    if not match:
        return None
    return match.group("name").strip()


def _dedupe_recent(
    commands: list[RepresentativeCommand],
    limit: int = _DEFAULT_REPRESENTATIVE_LIMIT,
) -> list[RepresentativeCommand]:
    """Keep recent commands while removing duplicates by case and command."""
    seen: set[tuple[str, str]] = set()
    selected: list[RepresentativeCommand] = []
    for command in reversed(commands):
        key = (command.case_name, command.command)
        if key in seen:
            continue
        seen.add(key)
        selected.append(command)
        if len(selected) == limit:
            break
    selected.reverse()
    return selected


def collect_representative_commands(
    log_paths: list[Path],
) -> dict[str, list[RepresentativeCommand]]:
    """Parse usage logs into representative smoke command groups.

    Args:
        log_paths: Existing log files.

    Returns:
        Mapping of smoke case names to representative commands.

    """
    grouped: dict[str, list[RepresentativeCommand]] = {
        "start_stop": [],
        "missing_tag": [],
        "list_entries": [],
        "status_json": [],
    }

    pending_query: str | None = None
    pending_start_from_run: bool = False

    for path in log_paths:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue

            query_match = re.search(r"(?:^|\s)query=(?P<query>.+)$", line)
            if query_match:
                pending_query = query_match.group("query").strip()
                continue

            if line.startswith("RUN: clocky start "):
                pending_start_from_run = True
                command = line.removeprefix("RUN: ").strip()
                grouped["start_stop"].append(
                    RepresentativeCommand(
                        case_name="start_stop",
                        command=command,
                        project_name=None,
                        source_path=path,
                    )
                )
                continue

            if line.startswith("RUN: clocky list"):
                grouped["list_entries"].append(
                    RepresentativeCommand(
                        case_name="list_entries",
                        command=line.removeprefix("RUN: ").strip(),
                        project_name=None,
                        source_path=path,
                    )
                )
                continue

            if line.startswith("RUN: clocky --json status"):
                grouped["status_json"].append(
                    RepresentativeCommand(
                        case_name="status_json",
                        command=line.removeprefix("RUN: ").strip(),
                        project_name=None,
                        source_path=path,
                    )
                )
                continue

            project_name = _extract_project_name(line)
            if project_name and (
                "clocky start output:" in line or line.startswith("stdout=Project:")
            ):
                command = f'clocky start --non-interactive "{pending_query or project_name}"'
                grouped["start_stop"].append(
                    RepresentativeCommand(
                        case_name="start_stop",
                        command=command,
                        project_name=project_name,
                        source_path=path,
                    )
                )
                pending_start_from_run = False
                continue

            if pending_start_from_run and project_name and line.startswith("Project:"):
                grouped["start_stop"].append(
                    RepresentativeCommand(
                        case_name="start_stop",
                        command=f'clocky start --non-interactive "{project_name}"',
                        project_name=project_name,
                        source_path=path,
                    )
                )
                pending_start_from_run = False
                continue

            missing_tag_match = _MISSING_TAG_RE.search(line)
            if missing_tag_match:
                missing_project = missing_tag_match.group("name").strip()
                grouped["missing_tag"].append(
                    RepresentativeCommand(
                        case_name="missing_tag",
                        command=(
                            f'clocky start --non-interactive "{pending_query or missing_project}"'
                        ),
                        project_name=missing_project,
                        source_path=path,
                    )
                )
                pending_start_from_run = False

    return {
        case_name: _dedupe_recent(commands) for case_name, commands in grouped.items() if commands
    }


def build_smoke_plan(repo_root: Path | None = None) -> SmokePlan:
    """Build a smoke plan from usage logs with Dribia-specific fallbacks.

    Environment variables override all other selection:
    ``CLOCKY_TEST_PROJECT`` and ``CLOCKY_TEST_PROJECT_MISSING_TAG``.

    Args:
        repo_root: Repository root. Defaults to the parent of this module.

    Returns:
        Smoke plan describing selected projects and representative commands.

    """
    start_override = os.environ.get("CLOCKY_TEST_PROJECT")
    missing_override = os.environ.get("CLOCKY_TEST_PROJECT_MISSING_TAG")
    log_paths = discover_usage_logs(repo_root)
    representatives = collect_representative_commands(log_paths)

    fallback_cases: list[str] = []

    start_stop_project = start_override
    if start_stop_project is None:
        start_stop_project = next(
            (
                command.project_name
                for command in representatives.get("start_stop", [])
                if command.project_name
            ),
            None,
        )
    if start_stop_project is None:
        start_stop_project = DEFAULT_START_STOP_PROJECT
        fallback_cases.append("start_stop")

    missing_tag_project = missing_override
    if missing_tag_project is None:
        missing_tag_project = next(
            (
                command.project_name
                for command in representatives.get("missing_tag", [])
                if command.project_name
            ),
            None,
        )
    if missing_tag_project is None:
        missing_tag_project = DEFAULT_MISSING_TAG_PROJECT
        fallback_cases.append("missing_tag")

    if "list_entries" not in representatives:
        representatives["list_entries"] = [
            RepresentativeCommand(
                case_name="list_entries",
                command=DEFAULT_LIST_COMMAND,
                project_name=None,
                source_path=Path("<fallback>"),
            )
        ]
        fallback_cases.append("list_entries")

    if "status_json" not in representatives:
        representatives["status_json"] = [
            RepresentativeCommand(
                case_name="status_json",
                command=DEFAULT_STATUS_JSON_COMMAND,
                project_name=None,
                source_path=Path("<fallback>"),
            )
        ]
        fallback_cases.append("status_json")

    return SmokePlan(
        start_stop_project=start_stop_project,
        missing_tag_project=missing_tag_project,
        representatives=representatives,
        fallback_cases=tuple(dict.fromkeys(fallback_cases)),
        log_paths=tuple(log_paths),
    )


def smoke_plan_to_lines(plan: SmokePlan) -> list[str]:
    """Render a smoke plan as readable lines."""
    lines = [
        f"start_stop project: {plan.start_stop_project}",
        f"missing_tag project: {plan.missing_tag_project}",
        f"log sources: {', '.join(str(path) for path in plan.log_paths) or '<none>'}",
        f"fallback cases: {', '.join(plan.fallback_cases) or '<none>'}",
    ]
    for case_name in ("start_stop", "missing_tag", "list_entries", "status_json"):
        commands = plan.representatives.get(case_name, [])
        if not commands:
            continue
        lines.append(f"{case_name} representatives:")
        for command in commands:
            source = command.source_path
            lines.append(f"  - {command.command} [{source}]")
    return lines


def smoke_plan_to_dict(plan: SmokePlan) -> dict[str, object]:
    """Convert a smoke plan to JSON-friendly data."""
    return {
        "start_stop_project": plan.start_stop_project,
        "missing_tag_project": plan.missing_tag_project,
        "log_paths": [str(path) for path in plan.log_paths],
        "fallback_cases": list(plan.fallback_cases),
        "representatives": {
            case_name: [
                {
                    "command": command.command,
                    "project_name": command.project_name,
                    "source_path": str(command.source_path),
                }
                for command in commands
            ]
            for case_name, commands in plan.representatives.items()
        },
    }
