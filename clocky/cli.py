"""clocky-cli — Clockify command-line interface.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Annotated

import questionary
import typer
from rich.console import Console

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
from clocky.fuzzy import fuzzy_search
from clocky.models import StartTimerRequest, StopTimerRequest

app = typer.Typer(
    name="clocky",
    help="A CLI to interact with your Clockify account.",
    add_completion=True,
)

console = Console()


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

    In interactive mode, shows a questionary picker if multiple matches.
    In non-interactive mode, returns the top match.

    Args:
        matches: List of (item, score) pairs.
        attr: Attribute name used for display.
        non_interactive: If True, never prompt; returns top match.

    Returns:
        The chosen item, or None if cancelled.

    """
    if len(matches) == 1:
        return matches[0][0]

    if non_interactive:
        return matches[0][0]

    choices = [
        questionary.Choice(f"{getattr(item, attr)}  ({score:.0f}%)", value=item)
        for item, score in matches
    ]
    choices.append(questionary.Choice("[Cancel]", value=None))
    return questionary.select("Pick one:", choices=choices).ask()


def _infer_tag_for_project(
    project_id: str,
    workspace_id: str,
    user_id: str,
) -> str | None:
    """Infer the most likely tag for a project based on recent entries.

    Looks at the last 50 entries for this project and returns the most
    commonly used tag ID, if any.
    """
    from clocky.context import build_context

    ctx = build_context()
    entries = ctx.api.get_time_entries(workspace_id, user_id, limit=50)

    # Filter entries for this project and collect tag usage
    tag_counts: Counter[str] = Counter()
    for entry in entries:
        if entry.project_id == project_id and entry.tag_ids:
            for tag_id in entry.tag_ids:
                tag_counts[tag_id] += 1

    if not tag_counts:
        return None

    # Return the most common tag
    most_common_tag_id, _count = tag_counts.most_common(1)[0]
    return most_common_tag_id


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
    ctx = build_context()
    entry = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)

    if not entry:
        print_no_timer()
        return

    project_name = None
    if entry.project_id:
        projects = {p.id: p.name for p in ctx.api.get_projects(ctx.workspace_id)}
        project_name = projects.get(entry.project_id)

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
) -> None:
    """Start a new timer."""
    ctx = build_context()

    all_projects = ctx.api.get_projects(ctx.workspace_id)
    matches = fuzzy_search(project, all_projects, key=lambda p: p.name)
    if not matches:
        print_error(f"No projects matching '{project}'")
        raise typer.Exit(1)
    chosen = _pick_one(matches, "name", non_interactive=non_interactive)
    if not chosen:
        raise typer.Exit(0)

    project_id: str | None = chosen.id
    console.print(f"[dim]Project:[/dim] [cyan]{chosen.name}[/cyan]")

    tag_ids: list[str] = []

    # Explicit tags override auto-tag
    if tags is not None:
        all_tags = ctx.api.get_tags(ctx.workspace_id)
        for t in tags:
            tag_matches = fuzzy_search(t, all_tags, key=lambda tag: tag.name)
            if not tag_matches:
                print_error(f"Tag '{t}' not found, skipping")
                continue
            chosen_tag = _pick_one(tag_matches, "name")
            if chosen_tag:
                tag_ids.append(chosen_tag.id)
    elif auto_tag and project_id:
        # Infer tag from recent entries for this project
        inferred_tag_id = _infer_tag_for_project(project_id, ctx.workspace_id, ctx.user.id)
        if inferred_tag_id:
            tag_ids.append(inferred_tag_id)
            # Get tag name for display
            all_tags = ctx.api.get_tags(ctx.workspace_id)
            tag_name = next((t.name for t in all_tags if t.id == inferred_tag_id), inferred_tag_id)
            console.print(f"[dim]Tag (auto):[/dim] [magenta]{tag_name}[/magenta]")

    request = StartTimerRequest(
        start=_now_utc(),
        description=description,
        project_id=project_id,
        tag_ids=tag_ids,
    )
    entry = ctx.api.start_timer(ctx.workspace_id, request)
    msg = f"Timer started{f' — {description}' if description else ''}"
    print_success(f"{msg}  [dim](id: {entry.id})[/dim]")


@app.command()
def stop() -> None:
    """Stop the currently running timer (if any)."""
    ctx = build_context()
    running = ctx.api.get_running_timer(ctx.workspace_id, ctx.user.id)

    if not running:
        print_no_timer()
        return

    entry = ctx.api.stop_timer(ctx.workspace_id, ctx.user.id, StopTimerRequest(end=_now_utc()))
    print_timer_stopped(entry)


@app.command("list")
def list_entries(
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of entries")] = 10,
) -> None:
    """List recent time entries."""
    ctx = build_context()
    entries = ctx.api.get_time_entries(ctx.workspace_id, ctx.user.id, limit=limit)
    project_map = {p.id: p.name for p in ctx.api.get_projects(ctx.workspace_id)}
    tag_map = {t.id: t.name for t in ctx.api.get_tags(ctx.workspace_id)}
    print_time_entries(entries, project_map, tag_map)


@app.command()
def projects(
    client: Annotated[str, typer.Argument(..., help="Client name to fuzzy-match")],
    search: Annotated[str, typer.Option("-s", "--search", help="Fuzzy search (optional)")] = "",
) -> None:
    """List projects for a client."""
    ctx = build_context()

    clients = ctx.api.get_clients(ctx.workspace_id)
    client_matches = fuzzy_search(client, clients, key=lambda c: c.name)
    if not client_matches:
        print_error(f"No clients matching '{client}'")
        raise typer.Exit(1)
    chosen_client = _pick_one(client_matches, "name")
    if not chosen_client:
        raise typer.Exit(0)

    client_label = chosen_client.name
    all_projects = [
        p for p in ctx.api.get_projects(ctx.workspace_id) if p.client_id == chosen_client.id
    ]

    if search:
        proj_matches = fuzzy_search(search, all_projects, key=lambda p: p.name)
        if not proj_matches:
            print_error(f"No projects matching '{search}'")
            raise typer.Exit(1)
        all_projects = [p for p, _ in proj_matches]

    print_projects(all_projects, client_filter=client_label)


def main() -> None:
    """Entry point."""
    app()
