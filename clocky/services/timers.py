# SPDX-License-Identifier: MIT
"""Timer-oriented application services.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from clocky.api import ClockifyAPIError
from clocky.cli_helpers.selection import pick_one
from clocky.cli_helpers.tagging import resolve_tag_ids
from clocky.context import AppContext
from clocky.fuzzy import SEARCH_HISTORY_LIMIT, fuzzy_search_projects
from clocky.lookup import build_project_map, build_tag_map, resolve_project_name, resolve_tag_names
from clocky.models import Project, StartTimerRequest, StopTimerRequest, TimeEntry
from clocky.services.errors import ServiceUsageError


@dataclass(frozen=True)
class StatusData:
    """Resolved status payload for the current running timer."""

    entry: TimeEntry | None
    project_name: str | None = None
    tag_names: list[str] | None = None


@dataclass(frozen=True)
class StartTimerData:
    """Resolved payload for a start-timer workflow."""

    project: Project
    description: str
    tag_ids: list[str]
    tag_names: list[str]
    entry: TimeEntry | None = None
    dry_run: bool = False
    stopped_previous: bool = False


@dataclass(frozen=True)
class StopTimerData:
    """Resolved payload for a stop-timer workflow."""

    entry: TimeEntry | None
    project_name: str | None = None
    tag_names: list[str] | None = None
    elapsed: timedelta | None = None


@dataclass(frozen=True)
class TimeEntriesData:
    """Resolved data for listing time entries."""

    entries: list[TimeEntry]
    project_map: dict[str, str]
    tag_map: dict[str, str]


@dataclass(frozen=True)
class DeleteEntryData:
    """Payload for delete confirmation."""

    entry_id: str


def now_utc() -> str:
    """Return current UTC time as a Clockify-compatible ISO string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_status_data(ctx: AppContext) -> StatusData:
    """Resolve status data for the current timer."""
    entry = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)
    if not entry:
        return StatusData(entry=None)

    project_name = None
    if entry.project_id:
        project_map = build_project_map(ctx.api, ctx.workspace_id)
        project_name = resolve_project_name(project_map, entry.project_id)

    tag_map = build_tag_map(ctx.api, ctx.workspace_id)
    tag_names = resolve_tag_names(tag_map, entry.tag_ids)
    return StatusData(entry=entry, project_name=project_name, tag_names=tag_names)


def start_timer(
    ctx: AppContext,
    project_query: str,
    description: str,
    tags: list[str] | None,
    *,
    auto_tag: bool,
    non_interactive: bool,
    dry_run: bool,
) -> StartTimerData | None:
    """Resolve and optionally start a timer.

    Returns ``None`` when the interactive selector is cancelled.

    Raises:
        ServiceUsageError: If no project matches the supplied query.

    """
    all_projects = ctx.api.get_projects(ctx.workspace_id)
    recent_entries = ctx.api.get_time_entries(
        ctx.workspace_id,
        ctx.user.id,
        limit=SEARCH_HISTORY_LIMIT,
    )
    matches = fuzzy_search_projects(project_query, all_projects, recent_entries)
    if not matches:
        raise ServiceUsageError(f"No projects matching '{project_query}'")

    chosen = pick_one(matches, "name", non_interactive=non_interactive)
    if not chosen:
        return None

    all_tags = ctx.api.get_tags(ctx.workspace_id)
    tag_ids = resolve_tag_ids(
        ctx.api,
        ctx.workspace_id,
        ctx.user.id,
        chosen.id,
        chosen.name,
        tags,
        all_tags,
        auto_tag=auto_tag,
        non_interactive=non_interactive,
        recent_entries=recent_entries,
    )
    tag_map = {tag.id: tag.name for tag in all_tags}
    tag_names = resolve_tag_names(tag_map, tag_ids)

    if dry_run:
        return StartTimerData(
            project=chosen,
            description=description,
            tag_ids=tag_ids,
            tag_names=tag_names,
            dry_run=True,
        )

    running = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)
    stopped_previous = running is not None
    if running:
        ctx.api.stop_timer(ctx.workspace_id, ctx.user.id, StopTimerRequest(end=now_utc()))

    request = StartTimerRequest(
        start=now_utc(),
        description=description,
        project_id=chosen.id,
        tag_ids=tag_ids,
    )
    entry = ctx.api.start_timer(ctx.workspace_id, request)
    return StartTimerData(
        project=chosen,
        description=description,
        tag_ids=tag_ids,
        tag_names=tag_names,
        entry=entry,
        stopped_previous=stopped_previous,
    )


def stop_timer(ctx: AppContext) -> StopTimerData:
    """Stop the current timer and resolve display data."""
    running = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)
    if not running:
        return StopTimerData(entry=None)

    started = running.time_interval.start
    started_utc = started if started.tzinfo else started.replace(tzinfo=UTC)
    elapsed = datetime.now(UTC) - started_utc
    entry = ctx.api.stop_timer(ctx.workspace_id, ctx.user.id, StopTimerRequest(end=now_utc()))

    project_name = None
    if entry.project_id:
        project_map = build_project_map(ctx.api, ctx.workspace_id)
        project_name = resolve_project_name(project_map, entry.project_id)
    tag_map = build_tag_map(ctx.api, ctx.workspace_id)
    tag_names = resolve_tag_names(tag_map, entry.tag_ids)
    return StopTimerData(
        entry=entry,
        project_name=project_name,
        tag_names=tag_names,
        elapsed=elapsed,
    )


def list_time_entries(ctx: AppContext, limit: int) -> TimeEntriesData:
    """Resolve recent time entries and lookup maps."""
    entries = ctx.api.get_time_entries(ctx.workspace_id, ctx.user.id, limit=limit)
    project_map = build_project_map(ctx.api, ctx.workspace_id)
    tag_map = build_tag_map(ctx.api, ctx.workspace_id)
    return TimeEntriesData(entries=entries, project_map=project_map, tag_map=tag_map)


def delete_time_entry(ctx: AppContext, entry_id: str) -> DeleteEntryData:
    """Delete a time entry and return confirmation data."""
    ctx.api.delete_time_entry(ctx.workspace_id, entry_id)
    return DeleteEntryData(entry_id=entry_id)


__all__ = [
    "DeleteEntryData",
    "StartTimerData",
    "StatusData",
    "StopTimerData",
    "TimeEntriesData",
    "delete_time_entry",
    "get_status_data",
    "list_time_entries",
    "now_utc",
    "start_timer",
    "ServiceUsageError",
    "stop_timer",
    "ClockifyAPIError",
]
