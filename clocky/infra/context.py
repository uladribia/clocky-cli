"""Application context — resolves API client, user, and workspace.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from clocky.domain.models import User
from clocky.infra.api import ClockifyAPI
from clocky.infra.config import load_settings
from clocky.infra.gateway import ClockifyGateway


@dataclass
class AppContext:
    """Holds API client, user, and workspace ID for the session."""

    api: ClockifyGateway
    user: User
    workspace_id: str

    def close(self) -> None:
        """Close the underlying API client."""
        self.api.close()

    def __enter__(self) -> AppContext:
        """Return the active context manager instance."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Ensure the API client is closed after use."""
        del exc_type, exc, tb
        self.close()


def build_context() -> AppContext:
    """Load settings, authenticate, and resolve workspace.

    Uses CLOCKIFY_WORKSPACE_ID from config if set, otherwise the user's default.
    """
    settings = load_settings()
    api = ClockifyAPI(api_key=settings.clockify_api_key)
    user = api.get_user()
    workspace_id = settings.clockify_workspace_id or user.default_workspace
    return AppContext(api=api, user=user, workspace_id=workspace_id)
