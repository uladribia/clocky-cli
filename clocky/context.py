"""Application context — resolves API client, user, and workspace.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from clocky.api import ClockifyAPI
from clocky.config import load_settings
from clocky.models import User


@dataclass
class AppContext:
    """Holds API client, user, and workspace ID for the session."""

    api: ClockifyAPI
    user: User
    workspace_id: str


def build_context() -> AppContext:
    """Load settings, authenticate, and resolve workspace.

    Uses CLOCKIFY_WORKSPACE_ID from config if set, otherwise the user's default.
    """
    settings = load_settings()
    api = ClockifyAPI(api_key=settings.clockify_api_key)
    user = api.get_user()
    workspace_id = settings.clockify_workspace_id or user.default_workspace
    return AppContext(api=api, user=user, workspace_id=workspace_id)
