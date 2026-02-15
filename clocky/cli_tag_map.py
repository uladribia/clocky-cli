"""CLI commands for managing the project→tag mapping.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import typer

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
