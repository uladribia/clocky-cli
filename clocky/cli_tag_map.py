# SPDX-License-Identifier: MIT
"""CLI commands for managing the project→tag mapping.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import questionary
import typer

from clocky.cli_helpers.selection import fuzzy_choices
from clocky.context import build_context
from clocky.fuzzy import SEARCH_HISTORY_LIMIT, fuzzy_search_projects, fuzzy_search_tags
from clocky.tag_map import TagMap, tag_map_path

if TYPE_CHECKING:
    from rich.console import Console


def _name_for_id(items: list[Any], id_: str) -> str:
    """Return the ``name`` of the first item whose ``id`` matches, or ``id_`` as fallback.

    Args:
        items: Objects with ``.id`` and ``.name`` attributes.
        id_: The ID to look up.

    Returns:
        Matching name, or ``id_`` when no match is found.

    """
    return next((x.name for x in items if x.id == id_), id_)


def _load_json_object(text: str) -> dict[str, str]:
    """Parse edited tag-map JSON into a normalised string-to-string mapping."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise typer.BadParameter("Tag map must be a JSON object (project_id -> tag_id)")

    return {str(key): str(value) for key, value in data.items()}


def _resolve_mapping_names(
    mapping: dict[str, str],
    projects: dict[str, str],
    tags: dict[str, str],
) -> dict[str, str]:
    """Resolve persisted project/tag IDs to human-readable names."""
    return {
        projects.get(project_id, project_id): tags.get(tag_id, tag_id)
        for project_id, tag_id in mapping.items()
    }


def register(app: typer.Typer, console: Console) -> None:
    """Register tag-map subcommands.

    Args:
        app: Parent Typer app.
        console: Rich console for output.

    """
    tag_app = typer.Typer(help="Manage the persisted project→tag mapping.")
    app.add_typer(tag_app, name="tag-map")

    @tag_app.command("show")
    def show() -> None:
        """Show the tag map (project → tag) using names.

        The underlying file stores IDs, but this output resolves them to
        names for readability.
        """
        with build_context() as ctx:
            projects = {p.id: p.name for p in ctx.api.get_projects(ctx.workspace_id)}
            tags = {t.id: t.name for t in ctx.api.get_tags(ctx.workspace_id)}

        mapping = TagMap.load().project_to_tag
        resolved = _resolve_mapping_names(mapping, projects, tags)

        console.print(json.dumps(resolved, indent=2, sort_keys=True, ensure_ascii=False))
        console.print(f"\n[dim]Path:[/dim] {tag_map_path()}")

    @tag_app.command("edit")
    def edit() -> None:
        """Edit the tag map interactively in your $EDITOR."""
        path = tag_map_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("{}\n", encoding="utf-8")

        edited = typer.edit(path.read_text(encoding="utf-8"))
        if edited is None:
            return

        TagMap(project_to_tag=_load_json_object(edited)).save()
        console.print("[green]Saved.[/green]")

    @tag_app.command("set")
    def set_mapping(project_id: str, tag_id: str) -> None:
        """Set mapping for a project id.

        Note: this command accepts IDs. Prefer `clocky tag-map pick` for a
        name-based interactive flow.
        """
        TagMap.load().set(project_id, tag_id).save()

        with build_context() as ctx:
            projects = ctx.api.get_projects(ctx.workspace_id)
            tags = ctx.api.get_tags(ctx.workspace_id)
        project_name = _name_for_id(projects, project_id)
        tag_name = _name_for_id(tags, tag_id)

        console.print(f"[green]Mapped[/green] {project_name} → {tag_name}")

    @tag_app.command("pick")
    def pick() -> None:
        """Interactively choose a project and a tag, then persist the mapping.

        Uses fuzzy search + an interactive picker.
        """
        with build_context() as ctx:
            projects = ctx.api.get_projects(ctx.workspace_id)
            tags = ctx.api.get_tags(ctx.workspace_id)
            recent_entries = ctx.api.get_time_entries(
                ctx.workspace_id,
                ctx.user.id,
                limit=SEARCH_HISTORY_LIMIT,
            )

        project_query = typer.prompt("Project (fuzzy)").strip()
        project_matches = fuzzy_search_projects(project_query, projects, recent_entries)
        if not project_matches:
            raise typer.BadParameter(f"No projects matching '{project_query}'")

        chosen_project = questionary.select(
            "Pick project:", choices=fuzzy_choices(project_matches)
        ).ask()
        if not chosen_project:
            return

        tag_query = typer.prompt(f"Tag for '{chosen_project.name}' (fuzzy)").strip()
        tag_matches = fuzzy_search_tags(
            tag_query,
            tags,
            recent_entries,
            project_id=chosen_project.id,
        )
        if not tag_matches:
            raise typer.BadParameter(f"No tags matching '{tag_query}'")

        chosen_tag = questionary.select("Pick tag:", choices=fuzzy_choices(tag_matches)).ask()
        if not chosen_tag:
            return

        TagMap.load().set(chosen_project.id, chosen_tag.id).save()
        console.print(f"[green]Mapped[/green] {chosen_project.name} → {chosen_tag.name}")

    @tag_app.command("remove")
    def remove(project_id: str) -> None:
        """Remove mapping for a project id."""
        mapping = TagMap.load().project_to_tag
        if project_id not in mapping:
            console.print("[dim]No mapping for that project id.[/dim]")
            return

        with build_context() as ctx:
            projects = ctx.api.get_projects(ctx.workspace_id)
        project_name = _name_for_id(projects, project_id)

        mapping.pop(project_id)
        TagMap(project_to_tag=mapping).save()
        console.print(f"[green]Removed[/green] mapping for {project_name}")
