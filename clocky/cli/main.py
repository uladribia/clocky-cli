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

from clocky.app.services.errors import ServiceUsageError
from clocky.app.services.projects import list_projects
from clocky.app.services.timers import (
    delete_time_entry,
    get_status_data,
    list_time_entries,
    start_timer,
    stop_timer,
)
from clocky.cli.output import emit_json, get_mode, set_mode, time_entry_to_dict
from clocky.infra.api import ClockifyAPIError
from clocky.infra.cli_smoke import (
    DEFAULT_CASES,
    DEFAULT_HISTORY_LIMIT,
    build_smoke_plan,
    render_smoke_plan,
    run_integration_smoke,
    smoke_plan_to_dict,
)
from clocky.infra.context import build_context
from clocky.ui.console import console
from clocky.ui.display import (
    print_error,
    print_no_timer,
    print_projects,
    print_status,
    print_success,
    print_time_entries,
    print_timer_stopped,
)

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


# Subcommands are registered below (see clocky.cli.tag_map).

# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@app.command()
def setup() -> None:
    """Run interactive setup to configure your API key."""
    from clocky.cli.setup_flow import setup as run_setup

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
            help="Reserved for compatibility; planning is log-driven.",
        ),
    ] = DEFAULT_HISTORY_LIMIT,
    plan: Annotated[
        bool,
        typer.Option("--plan", help="Print the selected smoke plan and exit."),
    ] = False,
) -> None:
    """Run real integration smoke tests against Clockify."""
    cases = case or list(DEFAULT_CASES)
    unknown = [name for name in cases if name not in DEFAULT_CASES]
    if unknown:
        raise typer.BadParameter(f"Unknown case(s): {', '.join(unknown)}")

    if "CLOCKY_INTEGRATION_CLI" not in os.environ:
        os.environ["CLOCKY_INTEGRATION_CLI"] = f"{sys.executable} -m clocky.cli"

    if plan:
        smoke_plan = build_smoke_plan()
        if get_mode().json:
            emit_json(smoke_plan_to_dict(smoke_plan))
        else:
            sys.stdout.write(render_smoke_plan(smoke_plan))
        raise typer.Exit(0)

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
    with build_context() as ctx:
        data = get_status_data(ctx)

    if not data.entry:
        if mode.json:
            emit_json(None)
            return
        print_no_timer()
        return

    if mode.json:
        emit_json(
            time_entry_to_dict(
                data.entry,
                project_name=data.project_name,
                tag_names=data.tag_names,
            )
        )
        return

    print_status(data.entry, data.project_name)


@app.command()
def start(
    project: Annotated[str, typer.Argument(..., help="Active project name to fuzzy-search")],
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
    """Start a new timer on an active project."""
    mode = get_mode()
    with build_context() as ctx:
        try:
            data = start_timer(
                ctx,
                project,
                description,
                tags,
                auto_tag=auto_tag,
                non_interactive=non_interactive,
                dry_run=dry_run,
            )
        except ServiceUsageError as exc:
            print_error(f"clocky: {exc}")
            raise typer.Exit(2) from None
        except ClockifyAPIError as exc:
            print_error(f"clocky: {exc}")
            raise typer.Exit(1) from None

    if data is None:
        raise typer.Exit(0)

    if not mode.quiet:
        console.print(f"[dim]Project:[/dim] [cyan]{data.project.name}[/cyan]")
        if data.stopped_previous:
            console.print("[dim]Stopped previous timer.[/dim]")

    if data.dry_run:
        result = {
            "dry_run": True,
            "project": data.project.name,
            "project_id": data.project.id,
            "description": data.description,
            "tag_ids": data.tag_ids,
            "tag_names": data.tag_names,
        }
        if mode.json:
            emit_json(result)
        else:
            console.print("\n[bold yellow]Dry run[/bold yellow] — no timer started.")
            console.print(f"  Project:     [cyan]{data.project.name}[/cyan]")
            console.print(f"  Description: {description or '[dim]—[/dim]'}")
            tags_str = ", ".join(data.tag_names) if data.tag_names else "[dim]—[/dim]"
            console.print(f"  Tags:        [magenta]{tags_str}[/magenta]\n")
        return

    assert data.entry is not None
    if mode.json:
        emit_json(
            time_entry_to_dict(
                data.entry,
                project_name=data.project.name,
                tag_names=data.tag_names,
            )
        )
        return

    msg = f"Timer started{f' — {description}' if description else ''}"
    print_success(f"{msg}  [dim](id: {data.entry.id})[/dim]")


@app.command()
def stop(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation for long-running timers"),
    ] = False,
) -> None:
    """Stop the currently running timer (if any)."""
    mode = get_mode()
    with build_context() as ctx:
        status_data = get_status_data(ctx)
        if not status_data.entry:
            if mode.json:
                emit_json(None)
                return
            print_no_timer()
            return

        elapsed = datetime.now(UTC) - (
            status_data.entry.time_interval.start
            if status_data.entry.time_interval.start.tzinfo
            else status_data.entry.time_interval.start.replace(tzinfo=UTC)
        )
        if (
            elapsed.total_seconds() > 8 * 3600
            and not force
            and sys.stdin.isatty()
            and not mode.quiet
        ):
            from clocky.ui.display import format_duration

            confirm = typer.confirm(
                f"Timer has been running for {format_duration(elapsed)}. Stop it?"
            )
            if not confirm:
                raise typer.Exit(0)

        data = stop_timer(ctx)

    if data.entry is None:
        if mode.json:
            emit_json(None)
            return
        print_no_timer()
        return

    if mode.json:
        emit_json(
            time_entry_to_dict(
                data.entry,
                project_name=data.project_name,
                tag_names=data.tag_names,
            )
        )
        return

    print_timer_stopped(data.entry)


@app.command("list")
def list_entries(
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of entries")] = 10,
) -> None:
    """List recent time entries."""
    mode = get_mode()
    with build_context() as ctx:
        data = list_time_entries(ctx, limit)

    if mode.json:
        result = [
            time_entry_to_dict(
                entry,
                project_name=data.project_map.get(entry.project_id or ""),
                tag_names=[data.tag_map.get(tag_id, tag_id) for tag_id in entry.tag_ids],
            )
            for entry in data.entries
        ]
        emit_json(result)
        return

    print_time_entries(data.entries, data.project_map, data.tag_map)


@app.command()
def projects(
    client: Annotated[
        str | None, typer.Argument(help="Client name to fuzzy-match for active projects (optional)")
    ] = None,
    search: Annotated[
        str,
        typer.Option("-s", "--search", help="Fuzzy search active project names (optional)"),
    ] = "",
) -> None:
    """List active projects, optionally filtered by client."""
    mode = get_mode()
    with build_context() as ctx:
        try:
            data = list_projects(ctx, client, search)
        except ServiceUsageError as exc:
            print_error(f"clocky: {exc}")
            raise typer.Exit(2) from None

    if data is None:
        raise typer.Exit(0)

    if mode.json:
        result = [
            {
                "id": project.id,
                "name": project.name,
                "client_id": project.client_id,
                "client_name": project.client_name,
                "archived": project.archived,
            }
            for project in data.projects
        ]
        emit_json(result)
        return

    print_projects(data.projects, client_filter=data.client_label)


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
    with build_context() as ctx:
        if not force and sys.stdin.isatty() and not mode.quiet:
            confirm = typer.confirm(f"Delete time entry {entry_id}?")
            if not confirm:
                raise typer.Exit(0)

        data = delete_time_entry(ctx, entry_id)

    if mode.json:
        emit_json({"deleted": data.entry_id})
        return

    if not mode.quiet:
        print_success(f"Deleted entry [dim]{data.entry_id}[/dim]")


# Register subcommands at import time so they also appear in `--help`.
from clocky.cli.tag_map import register as _register_tag_map  # noqa: E402

_register_tag_map(app, console)


def main() -> None:
    """Entry point."""
    app()
