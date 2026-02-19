# SPDX-License-Identifier: MIT
"""clocky-cli — Clockify command-line interface.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version as _pkg_version
from typing import Annotated

import questionary
import typer
from rich.console import Console

from clocky.api import ClockifyAPI
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
from clocky.fuzzy import fuzzy_choices, fuzzy_search
from clocky.models import StartTimerRequest, StopTimerRequest, Tag
from clocky.output import emit_json, get_mode, set_mode, time_entry_to_dict
from clocky.tag_map import TagMap

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

_no_color = bool(os.environ.get("NO_COLOR"))
console = Console(no_color=_no_color)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _now_utc() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_one[T](
    matches: list[tuple[T, float]],
    attr: str,
    *,
    non_interactive: bool = False,
) -> T | None:
    """Select one item from fuzzy matches.

    Rules:
    - If there is only one match: return it.
    - If non-interactive: return best match.
    - If stdin is not a TTY (e.g. .desktop launch): return best match.
    - Otherwise: prompt user to pick.
    """
    if len(matches) == 1:
        return matches[0][0]

    if non_interactive or not sys.stdin.isatty():
        return matches[0][0]

    choices = fuzzy_choices(matches, attr)
    choices.append(questionary.Choice("[Cancel]", value=None))
    return questionary.select("Pick one:", choices=choices).ask()


def _infer_tag_for_project(
    api: ClockifyAPI,
    workspace_id: str,
    user_id: str,
    project_id: str,
) -> str | None:
    """Infer the most likely tag for a project based on recent entries.

    Looks at the last 50 entries for this project and returns the most
    commonly used tag ID, if any.

    Args:
        api: Clockify API client.
        workspace_id: Active workspace ID.
        user_id: Active user ID.
        project_id: Project to infer a tag for.

    Returns:
        The most commonly used tag ID, or None if no data exists.

    """
    entries = api.get_time_entries(workspace_id, user_id, limit=50)

    tag_counts: Counter[str] = Counter()
    for entry in entries:
        if entry.project_id == project_id and entry.tag_ids:
            for tag_id in entry.tag_ids:
                tag_counts[tag_id] += 1

    if not tag_counts:
        return None

    most_common_tag_id, _count = tag_counts.most_common(1)[0]
    return most_common_tag_id


def _resolve_tag_ids(
    api: ClockifyAPI,
    workspace_id: str,
    user_id: str,
    project_id: str,
    project_name: str,
    tags: list[str] | None,
    all_tags: list[Tag],
    *,
    auto_tag: bool,
    non_interactive: bool,
) -> list[str]:
    """Resolve tag IDs from explicit tags, stored mapping, history, or prompt.

    Priority: explicit ``--tag`` flags → stored project→tag mapping →
    history-based inference → interactive prompt.

    Args:
        api: Clockify API client.
        workspace_id: Active workspace ID.
        user_id: Active user ID.
        project_id: ID of the chosen project.
        project_name: Display name of the chosen project.
        tags: Explicit tag name(s) from ``--tag`` option, or ``None``.
        all_tags: All available tags in the workspace.
        auto_tag: Whether to infer a tag from recent history.
        non_interactive: Whether to suppress interactive prompts.

    Returns:
        List of resolved tag IDs (may be empty).

    Raises:
        typer.Exit: With code 1 when ``non_interactive`` is True and no tag
            mapping exists. Prints ``CLOCKY_ERROR_MISSING_TAG_MAP`` to
            stderr as a launcher-readable sentinel before exiting.

    """
    mode = get_mode()
    tags_by_id = {t.id: t for t in all_tags}
    tag_ids: list[str] = []

    if tags is not None:
        # Explicit tags: fuzzy-resolve each one and persist a 1:1 mapping when
        # exactly one tag is provided.
        for t in tags:
            tag_matches = fuzzy_search(t, all_tags, key=lambda tag: tag.name)
            if not tag_matches:
                print_error(f"Tag '{t}' not found, skipping")
                continue
            chosen_tag = _pick_one(tag_matches, "name", non_interactive=non_interactive)
            if chosen_tag:
                tag_ids.append(chosen_tag.id)
                if not mode.quiet:
                    console.print(
                        f"[dim]Tag (explicit):[/dim] [magenta]{chosen_tag.name}[/magenta]"
                    )

        if len(tag_ids) == 1:
            TagMap.load().set(project_id, tag_ids[0]).save()

    else:
        # No tags provided: stored mapping → history inference → interactive prompt
        tag_map = TagMap.load()
        mapped = tag_map.get(project_id)

        if mapped and mapped in tags_by_id:
            tag_ids.append(mapped)
            if not mode.quiet:
                console.print(
                    f"[dim]Tag (mapped):[/dim] [magenta]{tags_by_id[mapped].name}[/magenta]"
                )

        elif auto_tag:
            inferred = _infer_tag_for_project(api, workspace_id, user_id, project_id)
            if inferred and inferred in tags_by_id:
                tag_ids.append(inferred)
                if not mode.quiet:
                    console.print(
                        f"[dim]Tag (auto):[/dim] [magenta]{tags_by_id[inferred].name}[/magenta]"
                    )
                tag_map.set(project_id, inferred).save()

        if not tag_ids and sys.stdin.isatty():
            console.print(f"\nNo tag found for project [cyan]{project_name}[/cyan].")
            tag_query = typer.prompt("Tag (fuzzy)").strip()
            if tag_query:
                tag_matches = fuzzy_search(tag_query, all_tags, key=lambda tag: tag.name)
                if tag_matches:
                    chosen_tag = _pick_one(tag_matches, "name", non_interactive=non_interactive)
                    if chosen_tag:
                        tag_ids.append(chosen_tag.id)
                        tag_map.set(project_id, chosen_tag.id).save()
                        if not mode.quiet:
                            console.print(
                                f"[dim]Tag (chosen):[/dim] [magenta]{chosen_tag.name}[/magenta]"
                            )

        if not tag_ids and non_interactive:
            # Launcher-friendly sentinel for GUI scripts.
            Console(stderr=True).print("CLOCKY_ERROR_MISSING_TAG_MAP")
            print_error(
                f"No tag mapping found for '{project_name}'. Provide --tag once to set it, "
                "or let the launcher prompt you."
            )
            raise typer.Exit(1)

    return tag_ids


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@app.command()
def setup() -> None:
    """Run interactive setup to configure your API key."""
    from clocky.setup import setup as run_setup

    run_setup()


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
        projects = {p.id: p.name for p in ctx.api.get_projects(ctx.workspace_id)}
        project_name = projects.get(entry.project_id)

    if mode.json:
        tag_map = {t.id: t.name for t in ctx.api.get_tags(ctx.workspace_id)}
        tag_names = [tag_map.get(tid, tid) for tid in entry.tag_ids]
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
            help="Never prompt; auto-pick best fuzzy match",
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
    matches = fuzzy_search(project, all_projects, key=lambda p: p.name)
    if not matches:
        print_error(f"clocky: No projects matching '{project}'")
        raise typer.Exit(2)
    chosen = _pick_one(matches, "name", non_interactive=non_interactive)
    if not chosen:
        raise typer.Exit(0)

    if not mode.quiet:
        console.print(f"[dim]Project:[/dim] [cyan]{chosen.name}[/cyan]")

    all_tags = ctx.api.get_tags(ctx.workspace_id)
    tag_ids = _resolve_tag_ids(
        ctx.api,
        ctx.workspace_id,
        ctx.user.id,
        chosen.id,
        chosen.name,
        tags,
        all_tags,
        auto_tag=auto_tag,
        non_interactive=non_interactive,
    )

    tag_map = {t.id: t.name for t in all_tags}
    tag_names = [tag_map.get(tid, tid) for tid in tag_ids]

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

    request = StartTimerRequest(
        start=_now_utc(),
        description=description,
        project_id=chosen.id,
        tag_ids=tag_ids,
    )
    entry = ctx.api.start_timer(ctx.workspace_id, request)

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
            projects_map = {p.id: p.name for p in ctx.api.get_projects(ctx.workspace_id)}
            project_name = projects_map.get(entry.project_id)
        tag_map = {t.id: t.name for t in ctx.api.get_tags(ctx.workspace_id)}
        tag_names = [tag_map.get(tid, tid) for tid in entry.tag_ids]
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
    project_map = {p.id: p.name for p in ctx.api.get_projects(ctx.workspace_id)}
    tag_map = {t.id: t.name for t in ctx.api.get_tags(ctx.workspace_id)}

    if mode.json:
        result = [
            time_entry_to_dict(
                e,
                project_name=project_map.get(e.project_id or ""),
                tag_names=[tag_map.get(tid, tid) for tid in e.tag_ids],
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
        chosen_client = _pick_one(client_matches, "name")
        if not chosen_client:
            raise typer.Exit(0)

        client_label = chosen_client.name
        all_projects = [p for p in all_projects if p.client_id == chosen_client.id]

    if search:
        proj_matches = fuzzy_search(search, all_projects, key=lambda p: p.name)
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
