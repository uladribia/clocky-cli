# SPDX-License-Identifier: MIT
"""Interactive setup for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from clocky.browser import CLOCKIFY_API_KEY_URL, open_browser

CONFIG_DIR = Path.home() / ".config" / "clocky"
ENV_FILE = CONFIG_DIR / ".env"

console = Console()


def setup() -> None:
    """Run interactive setup to configure clocky."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]clocky-cli Setup[/bold cyan]\n\n"
            "This will configure your Clockify API key for global use.",
            border_style="cyan",
        )
    )

    # Check if already configured
    if ENV_FILE.exists():
        content = ENV_FILE.read_text()
        if "CLOCKIFY_API_KEY=" in content and "your_api_key_here" not in content:
            console.print(f"\n[green]✓[/green] Config already exists at: [dim]{ENV_FILE}[/dim]")
            if not Confirm.ask("Overwrite existing configuration?", default=False):
                console.print("[dim]Setup cancelled.[/dim]\n")
                return

    # Prompt for API key
    console.print("\n[bold]Step 1:[/bold] Get your API key from Clockify")
    console.print(f"  [dim]→ {CLOCKIFY_API_KEY_URL}[/dim]")

    if Confirm.ask("\n  Open Clockify settings in browser?", default=True):
        open_browser(CLOCKIFY_API_KEY_URL)
        console.print("  [dim]Browser opened.[/dim]")

    console.print("\n[bold]Step 2:[/bold] Paste your API key below")
    api_key = Prompt.ask("  API Key").strip()

    if not api_key:
        console.print("\n[red]✘[/red] No API key provided. Setup cancelled.\n")
        return

    # Optional workspace ID
    console.print("\n[bold]Step 3:[/bold] Workspace ID [dim](optional, press Enter to skip)[/dim]")
    console.print("  [dim]Leave empty to use your default workspace.[/dim]")
    workspace_id = Prompt.ask("  Workspace ID", default="").strip()

    # Create config directory and file
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    env_content = f"CLOCKIFY_API_KEY={api_key}\n"
    if workspace_id:
        env_content += f"CLOCKIFY_WORKSPACE_ID={workspace_id}\n"

    ENV_FILE.write_text(env_content)
    ENV_FILE.chmod(0o600)  # Secure permissions

    console.print(f"\n[green]✓[/green] Configuration saved to: [dim]{ENV_FILE}[/dim]")

    # Test the connection
    console.print("\n[bold]Step 4:[/bold] Testing connection...")
    try:
        from clocky.api import ClockifyAPI

        api = ClockifyAPI(api_key=api_key)
        user = api.get_user()
        console.print(f"  [green]✓[/green] Connected as: [bold]{user.name}[/bold] ({user.email})")
        api.close()
    except Exception as e:
        console.print(f"  [red]✘[/red] Connection failed: {e}")
        console.print("  [dim]Check your API key and try again.[/dim]")
        return

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("You can now use [bold]clocky[/bold] from anywhere.\n")
    console.print("  [dim]clocky status[/dim]      — check running timer")
    console.print("  [dim]clocky start -p X[/dim]  — start timer on project X")
    console.print("  [dim]clocky stop[/dim]        — stop timer")
    console.print("  [dim]clocky --help[/dim]      — see all commands\n")


if __name__ == "__main__":
    setup()
