# SPDX-License-Identifier: MIT
"""Tag inference and resolution helpers for CLI commands.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from clocky.display import print_error
from clocky.fuzzy import SEARCH_HISTORY_LIMIT, fuzzy_search_tags
from clocky.models import Tag, TimeEntry
from clocky.output import get_mode
from clocky.tag_map import TagMap

if TYPE_CHECKING:
    from clocky.api import ClockifyAPI

_no_color = bool(__import__("os").environ.get("NO_COLOR"))
console = Console(no_color=_no_color)


def infer_tag_for_project(
    api: ClockifyAPI,
    workspace_id: str,
    user_id: str,
    project_id: str,
    limit: int = 50,
    *,
    recent_entries: list[TimeEntry] | None = None,
) -> str | None:
    """Infer the most likely tag for a project based on recent entries.

    Looks at the last N entries for this project and returns the most
    commonly used tag ID, if any.

    Args:
        api: Clockify API client.
        workspace_id: Active workspace ID.
        user_id: Active user ID.
        project_id: Project to infer a tag for.
        limit: Number of recent entries to inspect.
        recent_entries: Optional pre-fetched recent entries.

    Returns:
        The most commonly used tag ID, or ``None`` if no data exists.

    """
    entries = recent_entries or api.get_time_entries(workspace_id, user_id, limit=limit)

    tag_counts: Counter[str] = Counter()
    for entry in entries:
        if entry.project_id == project_id and entry.tag_ids:
            for tag_id in entry.tag_ids:
                tag_counts[tag_id] += 1

    if not tag_counts:
        return None

    most_common_tag_id, _count = tag_counts.most_common(1)[0]
    return most_common_tag_id


def resolve_tag_ids(
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
    recent_entries: list[TimeEntry] | None = None,
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
        recent_entries: Optional pre-fetched recent entries.

    Returns:
        List of resolved tag IDs, which may be empty.

    Raises:
        typer.Exit: With code 1 when ``non_interactive`` is ``True`` and no tag
            mapping exists. Prints ``CLOCKY_ERROR_MISSING_TAG_MAP`` to stderr as
            a launcher-readable sentinel before exiting.

    """
    from clocky.cli_helpers.selection import pick_one

    mode = get_mode()
    tags_by_id = {t.id: t for t in all_tags}
    tag_ids: list[str] = []
    history = recent_entries or api.get_time_entries(
        workspace_id,
        user_id,
        limit=SEARCH_HISTORY_LIMIT,
    )

    if tags is not None:
        for tag_query in tags:
            tag_matches = fuzzy_search_tags(
                tag_query,
                all_tags,
                history,
                project_id=project_id,
            )
            if not tag_matches:
                print_error(f"Tag '{tag_query}' not found, skipping")
                continue
            chosen_tag = pick_one(tag_matches, "name", non_interactive=non_interactive)
            if chosen_tag:
                tag_ids.append(chosen_tag.id)
                if not mode.quiet:
                    console.print(
                        f"[dim]Tag (explicit):[/dim] [magenta]{chosen_tag.name}[/magenta]"
                    )

        if len(tag_ids) == 1:
            TagMap.load().set(project_id, tag_ids[0]).save()

    else:
        tag_map = TagMap.load()
        mapped = tag_map.get(project_id)

        if mapped and mapped in tags_by_id:
            tag_ids.append(mapped)
            if not mode.quiet:
                console.print(
                    f"[dim]Tag (mapped):[/dim] [magenta]{tags_by_id[mapped].name}[/magenta]"
                )

        elif auto_tag:
            inferred = infer_tag_for_project(
                api,
                workspace_id,
                user_id,
                project_id,
                recent_entries=history,
            )
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
                tag_matches = fuzzy_search_tags(
                    tag_query,
                    all_tags,
                    history,
                    project_id=project_id,
                )
                if tag_matches:
                    chosen_tag = pick_one(tag_matches, "name", non_interactive=non_interactive)
                    if chosen_tag:
                        tag_ids.append(chosen_tag.id)
                        tag_map.set(project_id, chosen_tag.id).save()
                        if not mode.quiet:
                            console.print(
                                f"[dim]Tag (chosen):[/dim] [magenta]{chosen_tag.name}[/magenta]"
                            )

        if not tag_ids and non_interactive:
            Console(stderr=True).print("CLOCKY_ERROR_MISSING_TAG_MAP")
            print_error(
                f"No tag mapping found for '{project_name}'. Provide --tag once to set it, "
                "or let the launcher prompt you."
            )
            raise typer.Exit(1)

    return tag_ids
