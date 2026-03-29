# SPDX-License-Identifier: MIT
"""Interactive setup for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from clocky.api import ClockifyAPI
from clocky.browser import CLOCKIFY_API_KEY_URL, open_browser
from clocky.setup_service import (
    APIClientFactory,
    detect_existing_config,
    verify_api_key,
    write_env_file,
)

CONFIG_DIR = Path.home() / ".config" / "clocky"
ENV_FILE = CONFIG_DIR / ".env"

console = Console()


def setup(
    *,
    env_file: Path = ENV_FILE,
    console_obj: Console = console,
    api_factory: APIClientFactory = ClockifyAPI,
) -> None:
    """Run interactive setup to configure clocky."""
    console_obj.print()
    console_obj.print(
        Panel(
            "[bold cyan]clocky-cli Setup[/bold cyan]\n\n"
            "This will configure your Clockify API key for global use.",
            border_style="cyan",
        )
    )

    existing = detect_existing_config(env_file)
    if existing.configured:
        console_obj.print(f"\n[green]✓[/green] Config already exists at: [dim]{env_file}[/dim]")
        if not Confirm.ask("Overwrite existing configuration?", default=False):
            console_obj.print("[dim]Setup cancelled.[/dim]\n")
            return

    console_obj.print("\n[bold]Step 1:[/bold] Get your API key from Clockify")
    console_obj.print(f"  [dim]→ {CLOCKIFY_API_KEY_URL}[/dim]")

    if Confirm.ask("\n  Open Clockify settings in browser?", default=True):
        open_browser(CLOCKIFY_API_KEY_URL)
        console_obj.print("  [dim]Browser opened.[/dim]")

    console_obj.print("\n[bold]Step 2:[/bold] Paste your API key below")
    api_key = Prompt.ask("  API Key").strip()

    if not api_key:
        console_obj.print("\n[red]✘[/red] No API key provided. Setup cancelled.\n")
        return

    console_obj.print(
        "\n[bold]Step 3:[/bold] Workspace ID [dim](optional, press Enter to skip)[/dim]"
    )
    console_obj.print("  [dim]Leave empty to use your default workspace.[/dim]")
    workspace_id = Prompt.ask("  Workspace ID", default="").strip()

    write_env_file(env_file, api_key, workspace_id)
    console_obj.print(f"\n[green]✓[/green] Configuration saved to: [dim]{env_file}[/dim]")

    console_obj.print("\n[bold]Step 4:[/bold] Testing connection...")
    result = verify_api_key(api_factory, api_key)
    if not result.success:
        console_obj.print(f"  [red]✘[/red] Connection failed: {result.error_message}")
        console_obj.print("  [dim]Check your API key and try again.[/dim]")
        return

    console_obj.print(
        f"  [green]✓[/green] Connected as: [bold]{result.user_name}[/bold] ({result.user_email})"
    )
    console_obj.print("\n[bold green]Setup complete![/bold green]")
    console_obj.print("You can now use [bold]clocky[/bold] from anywhere.\n")
    console_obj.print("  [dim]clocky status[/dim]      — check running timer")
    console_obj.print("  [dim]clocky start <project>[/dim] — start timer on a project")
    console_obj.print("  [dim]clocky stop[/dim]        — stop timer")
    console_obj.print("  [dim]clocky --help[/dim]      — see all commands\n")


if __name__ == "__main__":
    setup()
