# SPDX-License-Identifier: MIT
"""Project-oriented application services.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from clocky.app.services.errors import ServiceUsageError
from clocky.cli_helpers.selection import pick_one
from clocky.domain.fuzzy import SEARCH_HISTORY_LIMIT, fuzzy_search, fuzzy_search_projects
from clocky.domain.models import Project
from clocky.infra.context import AppContext


@dataclass(frozen=True)
class ProjectListData:
    """Resolved data for project listing commands."""

    projects: list[Project]
    client_label: str | None = None


def list_projects(
    ctx: AppContext, client_query: str | None, search_query: str
) -> ProjectListData | None:
    """Resolve filtered project listings.

    Returns ``None`` when an interactive selector is cancelled.

    Raises:
        ServiceUsageError: If a client or project query has no fuzzy matches.

    """
    client_label: str | None = None
    projects = ctx.api.get_projects(ctx.workspace_id)

    if client_query:
        clients = ctx.api.get_clients(ctx.workspace_id)
        client_matches = fuzzy_search(client_query, clients, key=lambda client: client.name)
        if not client_matches:
            raise ServiceUsageError(f"No clients matching '{client_query}'")

        chosen_client = pick_one(client_matches, "name")
        if not chosen_client:
            return None

        client_label = chosen_client.name
        projects = [project for project in projects if project.client_id == chosen_client.id]

    if search_query:
        recent_entries = ctx.api.get_time_entries(
            ctx.workspace_id,
            ctx.user.id,
            limit=SEARCH_HISTORY_LIMIT,
        )
        project_matches = fuzzy_search_projects(search_query, projects, recent_entries)
        if not project_matches:
            raise ServiceUsageError(f"No projects matching '{search_query}'")
        projects = [project for project, _score in project_matches]

    return ProjectListData(projects=projects, client_label=client_label)
