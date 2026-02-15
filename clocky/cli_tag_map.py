"""CLI commands for managing the project→tag mapping.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import questionary
import typer

from clocky.context import build_context
from clocky.fuzzy import fuzzy_search
from clocky.tag_map import TagMap, tag_map_path

if TYPE_CHECKING:
    from rich.console import Console


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
        """Show the tag map (project_id → tag_id)."""
        mapping = TagMap.load().project_to_tag
        console.print(json.dumps(mapping, indent=2, sort_keys=True))
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

        try:
            data = json.loads(edited)
        except json.JSONDecodeError as e:
            raise typer.BadParameter(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise typer.BadParameter("Tag map must be a JSON object (project_id -> tag_id)")

        TagMap(project_to_tag={str(k): str(v) for k, v in data.items()}).save()
        console.print("[green]Saved.[/green]")

    @tag_app.command("set")
    def set_mapping(project_id: str, tag_id: str) -> None:
        """Set mapping for a project id."""
        TagMap.load().set(project_id, tag_id).save()
        console.print(f"[green]Mapped[/green] {project_id} → {tag_id}")

    @tag_app.command("pick")
    def pick() -> None:
        """Interactively choose a project and a tag, then persist the mapping.

        Uses fuzzy search + an interactive picker.
        """
        ctx = build_context()

        projects = ctx.api.get_projects(ctx.workspace_id)
        tags = ctx.api.get_tags(ctx.workspace_id)

        project_query = typer.prompt("Project (fuzzy)").strip()
        project_matches = fuzzy_search(project_query, projects, key=lambda p: p.name)
        if not project_matches:
            raise typer.BadParameter(f"No projects matching '{project_query}'")

        proj_choices = [
            questionary.Choice(f"{p.name} ({score:.0f}%)", value=p) for p, score in project_matches
        ]
        chosen_project = questionary.select("Pick project:", choices=proj_choices).ask()
        if not chosen_project:
            return

        tag_query = typer.prompt(f"Tag for '{chosen_project.name}' (fuzzy)").strip()
        tag_matches = fuzzy_search(tag_query, tags, key=lambda t: t.name)
        if not tag_matches:
            raise typer.BadParameter(f"No tags matching '{tag_query}'")

        tag_choices = [
            questionary.Choice(f"{t.name} ({score:.0f}%)", value=t) for t, score in tag_matches
        ]
        chosen_tag = questionary.select("Pick tag:", choices=tag_choices).ask()
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
        mapping.pop(project_id)
        TagMap(project_to_tag=mapping).save()
        console.print(f"[green]Removed[/green] mapping for {project_id}")
