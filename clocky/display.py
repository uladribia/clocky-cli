# SPDX-License-Identifier: MIT
"""Rich-based display helpers for clocky-cli output.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rich import box
from rich.console import Console
from rich.table import Table

from clocky.models import Project, TimeEntry

console = Console()
err_console = Console(stderr=True)


def format_duration(delta: timedelta) -> str:
    """Format a timedelta as 'Xh Ym Zs'."""
    total = int(delta.total_seconds())
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC)."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _get_elapsed(start: datetime) -> str:
    """Get elapsed time from start until now."""
    return format_duration(datetime.now(UTC) - _ensure_utc(start))


def _get_duration(entry: TimeEntry) -> str:
    """Get duration string for a time entry."""
    interval = entry.time_interval
    if interval.end:
        delta = _ensure_utc(interval.end) - _ensure_utc(interval.start)
        return format_duration(delta)
    return interval.duration or "—"


def _print_table(table: Table) -> None:
    """Print a Rich table surrounded by blank lines."""
    console.print()
    console.print(table)
    console.print()


# -----------------------------------------------------------------------------
# Output functions
# -----------------------------------------------------------------------------


def print_status(entry: TimeEntry, project_name: str | None) -> None:
    """Print the currently running timer status."""
    elapsed = _get_elapsed(entry.time_interval.start)
    project = f"[bold cyan]{project_name}[/bold cyan]" if project_name else "[dim]No project[/dim]"
    desc = entry.description or "[dim]No description[/dim]"
    started = entry.time_interval.start.strftime("%Y-%m-%d %H:%M:%S")

    console.print()
    console.print("[bold green]⏱  Timer running[/bold green]")
    console.print(f"  Project:     {project}")
    console.print(f"  Description: {desc}")
    console.print(f"  Started:     {started} UTC")
    console.print(f"  Elapsed:     [bold yellow]{elapsed}[/bold yellow]")
    console.print()


def print_no_timer() -> None:
    """Print message when no timer is running."""
    console.print("\n[dim]No timer is currently running.[/dim]\n")


def print_timer_stopped(entry: TimeEntry) -> None:
    """Print confirmation that timer was stopped."""
    duration = _get_duration(entry)
    print_success(f"Timer stopped. Duration: [bold yellow]{duration}[/bold yellow]")


def print_time_entries(
    entries: list[TimeEntry],
    project_map: dict[str, str],
    tag_map: dict[str, str] | None = None,
) -> None:
    """Print a table of time entries.

    Args:
        entries: The time entries.
        project_map: Map of project_id -> project name.
        tag_map: Optional map of tag_id -> tag name.

    """
    if not entries:
        console.print("\n[dim]No time entries found.[/dim]\n")
        return

    table = Table(title="Recent Time Entries", box=box.ROUNDED, highlight=True)
    table.add_column("Date", style="dim", no_wrap=True)
    table.add_column("Project", style="cyan")
    table.add_column("Tags", style="magenta")
    table.add_column("Description")
    table.add_column("Duration", justify="right", style="yellow")

    tag_map = tag_map or {}

    for entry in entries:
        tags = "—"
        if entry.tag_ids:
            names = [tag_map.get(tid, tid) for tid in entry.tag_ids]
            tags = ", ".join(names)

        table.add_row(
            entry.time_interval.start.strftime("%Y-%m-%d %H:%M"),
            project_map.get(entry.project_id or "", "—"),
            tags,
            entry.description or "—",
            _get_duration(entry),
        )

    _print_table(table)


def print_projects(projects: list[Project], client_filter: str | None = None) -> None:
    """Print a table of projects."""
    if not projects:
        console.print("\n[dim]No projects found.[/dim]\n")
        return

    title = f"Projects — {client_filter}" if client_filter else "Projects"
    table = Table(title=title, box=box.ROUNDED, highlight=True)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="cyan")
    table.add_column("Client", style="magenta")

    for p in projects:
        table.add_row(p.id, p.name, p.client_name or "—")

    _print_table(table)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"\n[bold green]✔[/bold green] {message}\n")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    err_console.print(f"\n[bold red]✘[/bold red] {message}\n")
