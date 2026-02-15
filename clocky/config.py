"""Configuration loading from environment / .env file.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

CLOCKIFY_API_KEY_URL = "https://app.clockify.me/user/settings#apiKey"

_console = Console()
_err_console = Console(stderr=True)


def _find_env_file() -> Path:
    """Find .env file in standard locations.

    Search order:
    1. Current working directory (and parents)
    2. ~/.config/clocky/.env
    3. ~/.clocky.env

    Returns the first found, or ~/.config/clocky/.env as the default location.
    """
    # Search upward from cwd
    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / ".env"
        if candidate.exists():
            return candidate

    # Check XDG config location
    xdg_config = Path.home() / ".config" / "clocky" / ".env"
    if xdg_config.exists():
        return xdg_config

    # Check home directory
    home_env = Path.home() / ".clocky.env"
    if home_env.exists():
        return home_env

    # Default to XDG config location
    return xdg_config


def _open_browser(url: str) -> None:
    """Open URL in browser. Tries xdg-open first, falls back to webbrowser."""
    try:
        subprocess.run(["xdg-open", url], check=True, capture_output=True)  # noqa: S603, S607
    except (FileNotFoundError, subprocess.CalledProcessError):
        webbrowser.open(url)


def _prompt_open_browser() -> None:
    """Offer to open the Clockify API key page."""
    _console.print(f"\n  [bold cyan]Direct link:[/bold cyan] {CLOCKIFY_API_KEY_URL}")
    try:
        if Confirm.ask("\n  Open in browser?", default=True):
            _open_browser(CLOCKIFY_API_KEY_URL)
            _console.print("  [dim]Browser opened.[/dim]")
    except (KeyboardInterrupt, EOFError):
        pass  # Non-interactive


def _show_setup_guide(env_path: Path, *, file_exists: bool) -> None:
    """Show first-run setup instructions."""
    if file_exists:
        title = "[bold red]⚠  API key not set[/bold red]"
        body = (
            f"Found [bold].env[/bold] at: [dim]{env_path}[/dim]\n\n"
            "but [bold]CLOCKIFY_API_KEY[/bold] is missing or still a placeholder.\n\n"
            "[bold]Fix:[/bold]\n"
            "  1. Go to [bold]Profile Settings → API[/bold] on Clockify\n"
            "  2. Generate or copy your key\n"
            f"  3. Add to {env_path}:\n\n"
            "     [green]CLOCKIFY_API_KEY=your_key_here[/green]"
        )
    else:
        title = "[bold red]⚠  No .env file[/bold red]"
        body = (
            f"Create [bold].env[/bold] at: [dim]{env_path}[/dim]\n\n"
            "[bold]Fix:[/bold]\n"
            f"  1. [green]mkdir -p {env_path.parent}[/green]\n"
            f"  2. [green]echo 'CLOCKIFY_API_KEY=your_key' > {env_path}[/green]\n"
            "  3. Go to [bold]Profile Settings → API[/bold] on Clockify\n"
            "  4. Generate or copy your key and update the file"
        )

    _err_console.print()
    _err_console.print(Panel(body, title=title, border_style="red", padding=(1, 2)))
    _prompt_open_browser()
    _err_console.print()


class Settings(BaseSettings):
    """App settings from environment / .env file."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    clockify_api_key: str
    clockify_workspace_id: str = ""

    @field_validator("clockify_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure API key is present and not a placeholder."""
        v = v.strip()
        if not v or v == "your_api_key_here":
            raise ValueError("API key missing or placeholder")
        return v


def load_settings() -> Settings:
    """Load settings from .env, with helpful guidance on failure."""
    env_path = _find_env_file()

    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)

    try:
        return Settings(_env_file=env_path)  # type: ignore[call-arg]
    except Exception:
        _show_setup_guide(env_path, file_exists=env_path.exists())
        sys.exit(1)
