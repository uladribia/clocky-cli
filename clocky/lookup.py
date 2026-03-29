# SPDX-License-Identifier: MIT
"""Lookup utilities for projects and tags.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from clocky.gateway import ClockifyGateway


def build_project_map(api: ClockifyGateway, workspace_id: str) -> dict[str, str]:
    """Build a project ID to name mapping.

    Args:
        api: Clockify API client.
        workspace_id: Workspace ID.

    Returns:
        Dict mapping project ID to project name.

    """
    return {p.id: p.name for p in api.get_projects(workspace_id)}


def build_tag_map(api: ClockifyGateway, workspace_id: str) -> dict[str, str]:
    """Build a tag ID to name mapping.

    Args:
        api: Clockify API client.
        workspace_id: Workspace ID.

    Returns:
        Dict mapping tag ID to tag name.

    """
    return {t.id: t.name for t in api.get_tags(workspace_id)}


def resolve_project_name(project_map: dict[str, str], project_id: str | None) -> str | None:
    """Resolve project name from ID.

    Args:
        project_map: Project ID to name mapping.
        project_id: Project ID to look up.

    Returns:
        Project name, or None if not found.

    """
    if not project_id:
        return None
    return project_map.get(project_id)


def resolve_tag_names(tag_map: dict[str, str], tag_ids: list[str]) -> list[str]:
    """Resolve tag names from IDs.

    Args:
        tag_map: Tag ID to name mapping.
        tag_ids: List of tag IDs.

    Returns:
        List of tag names.

    """
    return [tag_map.get(tid, tid) for tid in tag_ids]
