# SPDX-License-Identifier: MIT
"""clocky-cli — Clockify command-line interface.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from importlib.metadata import version as _pkg_version
from typing import Annotated

import typer

from clocky.api import ClockifyAPIError
from clocky.cli_helpers.selection import pick_one
from clocky.cli_helpers.tagging import resolve_tag_ids
from clocky.console import console
from clocky.context import build_context
from clocky.display import (
    print_error,
    print_no_timer,
    print_projects,
    print_status,
    print_success,
    print_time_entries,
    print_timer_stopped,
)
from clocky.fuzzy import SEARCH_HISTORY_LIMIT, fuzzy_search, fuzzy_search_projects
from clocky.integration_smoke import DEFAULT_CASES, DEFAULT_HISTORY_LIMIT, run_integration_smoke
from clocky.lookup import build_project_map, build_tag_map, resolve_project_name, resolve_tag_names
from clocky.models import StartTimerRequest, StopTimerRequest
from clocky.output import emit_json, get_mode, set_mode, time_entry_to_dict

app = typer.Typer(
    name="clocky",
    help="A CLI to interact with your Clockify account.",
    add_completion=True,
)


def _version_callback(value: bool) -> None:
    """Print the package version and exit when ``--version`` is passed."""
    if value:
        typer.echo(f"clocky {_pkg_version('clocky-cli')}")
        raise typer.Exit()


@app.callback()
def _main_options(
    _version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output JSON (implies --quiet).",
        is_eager=True,
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress informational output.",
        is_eager=True,
    ),
) -> None:
    """Interact with your Clockify account."""
    set_mode(json_mode=json_output, quiet=quiet or json_output)


# Subcommands are registered below (see clocky.cli_tag_map).

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _now_utc() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@app.command()
def setup() -> None:
    """Run interactive setup to configure your API key."""
    from clocky.setup import setup as run_setup

    run_setup()


@app.command("integration-test")
def integration_test(
    case: Annotated[
        list[str] | None,
        typer.Option("--case", help="Case to run (repeatable)."),
    ] = None,
    history_limit: Annotated[
        int,
        typer.Option(
            "--history-limit",
            help="Number of recent time entries to inspect for project selection.",
        ),
    ] = DEFAULT_HISTORY_LIMIT,
) -> None:
    """Run real integration smoke tests against Clockify."""
    cases = case or list(DEFAULT_CASES)
    unknown = [name for name in cases if name not in DEFAULT_CASES]
    if unknown:
        raise typer.BadParameter(f"Unknown case(s): {', '.join(unknown)}")

    if "CLOCKY_INTEGRATION_CLI" not in os.environ:
        argv0 = sys.argv[0]
        if os.path.basename(argv0) in {"clocky", "clocky.exe"}:
            os.environ["CLOCKY_INTEGRATION_CLI"] = argv0
        else:
            os.environ["CLOCKY_INTEGRATION_CLI"] = (
                f'{sys.executable} -c "from clocky.cli import main; main()"'
            )

    try:
        exit_code = run_integration_smoke(cases, history_limit)
    except RuntimeError as exc:
        print_error(f"clocky: {exc}")
        raise typer.Exit(1) from None

    raise typer.Exit(exit_code)


@app.command()
def status() -> None:
    """Show the currently running timer."""
    mode = get_mode()
    ctx = build_context()
    entry = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)

    if not entry:
        if mode.json:
            emit_json(None)
            return
        print_no_timer()
        return

    project_name = None
    if entry.project_id:
        project_map = build_project_map(ctx.api, ctx.workspace_id)
        project_name = resolve_project_name(project_map, entry.project_id)

    if mode.json:
        tag_map = build_tag_map(ctx.api, ctx.workspace_id)
        tag_names = resolve_tag_names(tag_map, entry.tag_ids)
        emit_json(time_entry_to_dict(entry, project_name=project_name, tag_names=tag_names))
        return

    print_status(entry, project_name)


@app.command()
def start(
    project: Annotated[str, typer.Argument(..., help="Project name to fuzzy-search")],
    description: Annotated[str, typer.Option("-d", "--description", help="Description")] = "",
    tags: Annotated[list[str] | None, typer.Option("-t", "--tag", help="Tag name(s)")] = None,
    auto_tag: Annotated[
        bool, typer.Option("--auto-tag/--no-auto-tag", help="Auto-infer tag from history")
    ] = True,
    non_interactive: Annotated[
        bool,
        typer.Option(
            "--non-interactive/--interactive",
            help="Never prompt; auto-pick the top weighted match",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview what would happen without starting a timer"),
    ] = False,
) -> None:
    """Start a new timer."""
    mode = get_mode()
    ctx = build_context()

    all_projects = ctx.api.get_projects(ctx.workspace_id)
    recent_entries = ctx.api.get_time_entries(
        ctx.workspace_id,
        ctx.user.id,
        limit=SEARCH_HISTORY_LIMIT,
    )
    matches = fuzzy_search_projects(project, all_projects, recent_entries)
    if not matches:
        print_error(f"clocky: No projects matching '{project}'")
        raise typer.Exit(2)
    chosen = pick_one(matches, "name", non_interactive=non_interactive)
    if not chosen:
        raise typer.Exit(0)

    if not mode.quiet:
        console.print(f"[dim]Project:[/dim] [cyan]{chosen.name}[/cyan]")

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

    tag_map = {t.id: t.name for t in all_tags}
    tag_names = resolve_tag_names(tag_map, tag_ids)

    if dry_run:
        result = {
            "dry_run": True,
            "project": chosen.name,
            "project_id": chosen.id,
            "description": description,
            "tag_ids": tag_ids,
            "tag_names": tag_names,
        }
        if mode.json:
            emit_json(result)
        else:
            console.print("\n[bold yellow]Dry run[/bold yellow] — no timer started.")
            console.print(f"  Project:     [cyan]{chosen.name}[/cyan]")
            console.print(f"  Description: {description or '[dim]—[/dim]'}")
            tags_str = ", ".join(tag_names) if tag_names else "[dim]—[/dim]"
            console.print(f"  Tags:        [magenta]{tags_str}[/magenta]\n")
        return

    # Stop any running timer before starting a new one.
    running = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)
    if running:
        ctx.api.stop_timer(ctx.workspace_id, ctx.user.id, StopTimerRequest(end=_now_utc()))
        if not mode.quiet:
            console.print("[dim]Stopped previous timer.[/dim]")

    request = StartTimerRequest(
        start=_now_utc(),
        description=description,
        project_id=chosen.id,
        tag_ids=tag_ids,
    )
    try:
        entry = ctx.api.start_timer(ctx.workspace_id, request)
    except ClockifyAPIError as exc:
        print_error(f"clocky: {exc}")
        raise typer.Exit(1) from None

    if mode.json:
        emit_json(time_entry_to_dict(entry, project_name=chosen.name, tag_names=tag_names))
        return

    msg = f"Timer started{f' — {description}' if description else ''}"
    print_success(f"{msg}  [dim](id: {entry.id})[/dim]")


@app.command()
def stop(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation for long-running timers"),
    ] = False,
) -> None:
    """Stop the currently running timer (if any)."""
    mode = get_mode()
    ctx = build_context()
    running = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)

    if not running:
        if mode.json:
            emit_json(None)
            return
        print_no_timer()
        return

    # Warn on long-running timers (>8h) when interactive
    elapsed = datetime.now(UTC) - (
        running.time_interval.start
        if running.time_interval.start.tzinfo
        else running.time_interval.start.replace(tzinfo=UTC)
    )
    if elapsed.total_seconds() > 8 * 3600 and not force and sys.stdin.isatty() and not mode.quiet:
        from clocky.display import format_duration

        confirm = typer.confirm(f"Timer has been running for {format_duration(elapsed)}. Stop it?")
        if not confirm:
            raise typer.Exit(0)

    entry = ctx.api.stop_timer(ctx.workspace_id, ctx.user.id, StopTimerRequest(end=_now_utc()))

    if mode.json:
        project_name = None
        if entry.project_id:
            project_map = build_project_map(ctx.api, ctx.workspace_id)
            project_name = resolve_project_name(project_map, entry.project_id)
        tag_map = build_tag_map(ctx.api, ctx.workspace_id)
        tag_names = resolve_tag_names(tag_map, entry.tag_ids)
        emit_json(time_entry_to_dict(entry, project_name=project_name, tag_names=tag_names))
        return

    print_timer_stopped(entry)


@app.command("list")
def list_entries(
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of entries")] = 10,
) -> None:
    """List recent time entries."""
    mode = get_mode()
    ctx = build_context()
    entries = ctx.api.get_time_entries(ctx.workspace_id, ctx.user.id, limit=limit)
    project_map = build_project_map(ctx.api, ctx.workspace_id)
    tag_map = build_tag_map(ctx.api, ctx.workspace_id)

    if mode.json:
        result = [
            time_entry_to_dict(
                e,
                project_name=resolve_project_name(project_map, e.project_id),
                tag_names=resolve_tag_names(tag_map, e.tag_ids),
            )
            for e in entries
        ]
        emit_json(result)
        return

    print_time_entries(entries, project_map, tag_map)


@app.command()
def projects(
    client: Annotated[
        str | None, typer.Argument(help="Client name to fuzzy-match (optional)")
    ] = None,
    search: Annotated[str, typer.Option("-s", "--search", help="Fuzzy search (optional)")] = "",
) -> None:
    """List projects, optionally filtered by client."""
    mode = get_mode()
    ctx = build_context()

    client_label: str | None = None
    all_projects = ctx.api.get_projects(ctx.workspace_id)

    if client:
        clients = ctx.api.get_clients(ctx.workspace_id)
        client_matches = fuzzy_search(client, clients, key=lambda c: c.name)
        if not client_matches:
            print_error(f"clocky: No clients matching '{client}'")
            raise typer.Exit(2)
        chosen_client = pick_one(client_matches, "name")
        if not chosen_client:
            raise typer.Exit(0)

        client_label = chosen_client.name
        all_projects = [p for p in all_projects if p.client_id == chosen_client.id]

    if search:
        recent_entries = ctx.api.get_time_entries(
            ctx.workspace_id,
            ctx.user.id,
            limit=SEARCH_HISTORY_LIMIT,
        )
        proj_matches = fuzzy_search_projects(search, all_projects, recent_entries)
        if not proj_matches:
            print_error(f"clocky: No projects matching '{search}'")
            raise typer.Exit(2)
        all_projects = [p for p, _ in proj_matches]

    if mode.json:
        result = [
            {
                "id": p.id,
                "name": p.name,
                "client_id": p.client_id,
                "client_name": p.client_name,
                "archived": p.archived,
            }
            for p in all_projects
        ]
        emit_json(result)
        return

    print_projects(all_projects, client_filter=client_label)


@app.command()
def delete(
    entry_id: Annotated[str, typer.Argument(help="Time entry ID to delete")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete a time entry by ID."""
    mode = get_mode()
    ctx = build_context()

    if not force and sys.stdin.isatty() and not mode.quiet:
        confirm = typer.confirm(f"Delete time entry {entry_id}?")
        if not confirm:
            raise typer.Exit(0)

    ctx.api.delete_time_entry(ctx.workspace_id, entry_id)

    if mode.json:
        emit_json({"deleted": entry_id})
        return

    if not mode.quiet:
        print_success(f"Deleted entry [dim]{entry_id}[/dim]")


# Register subcommands at import time so they also appear in `--help`.
from clocky.cli_tag_map import register as _register_tag_map  # noqa: E402

_register_tag_map(app, console)


def main() -> None:
    """Entry point."""
    app()
