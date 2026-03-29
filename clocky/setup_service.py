# SPDX-License-Identifier: MIT
"""Reusable setup workflow helpers.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from clocky.browser import CLOCKIFY_API_KEY_URL


class UserLookup(Protocol):
    """Minimal user shape returned by setup connection checks."""

    name: str
    email: str


class APIClient(Protocol):
    """Minimal API client shape used by setup verification."""

    def get_user(self) -> UserLookup:
        """Return the authenticated user."""

    def close(self) -> None:
        """Release resources held by the client."""


class APIClientFactory(Protocol):
    """Factory protocol for creating API clients during setup."""

    def __call__(self, api_key: str) -> APIClient:
        """Create a client for the provided API key."""


@dataclass(frozen=True)
class ExistingConfigState:
    """State derived from an existing configuration file."""

    exists: bool
    configured: bool


@dataclass(frozen=True)
class ConnectionCheckResult:
    """Outcome of validating a candidate API key."""

    success: bool
    user_name: str = ""
    user_email: str = ""
    error_message: str = ""


def detect_existing_config(env_file: Path) -> ExistingConfigState:
    """Inspect whether a configuration file already contains a real API key."""
    if not env_file.exists():
        return ExistingConfigState(exists=False, configured=False)

    content = env_file.read_text(encoding="utf-8")
    configured = "CLOCKIFY_API_KEY=" in content and "your_api_key_here" not in content
    return ExistingConfigState(exists=True, configured=configured)


def build_env_content(api_key: str, workspace_id: str) -> str:
    """Build the persisted `.env` content for setup."""
    content = f"CLOCKIFY_API_KEY={api_key}\n"
    if workspace_id:
        content += f"CLOCKIFY_WORKSPACE_ID={workspace_id}\n"
    return content


def write_env_file(env_file: Path, api_key: str, workspace_id: str) -> None:
    """Persist setup configuration with secure permissions when possible."""
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(build_env_content(api_key, workspace_id), encoding="utf-8")
    env_file.chmod(0o600)


def verify_api_key(api_factory: APIClientFactory, api_key: str) -> ConnectionCheckResult:
    """Verify a candidate API key using the provided API factory."""
    client = api_factory(api_key)
    try:
        user = client.get_user()
        return ConnectionCheckResult(success=True, user_name=user.name, user_email=user.email)
    except Exception as exc:  # noqa: BLE001
        return ConnectionCheckResult(success=False, error_message=str(exc))
    finally:
        client.close()


__all__ = [
    "APIClientFactory",
    "CLOCKIFY_API_KEY_URL",
    "ConnectionCheckResult",
    "ExistingConfigState",
    "build_env_content",
    "detect_existing_config",
    "verify_api_key",
    "write_env_file",
]
