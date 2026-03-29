"""Persistent project→tag mapping.

SPDX-License-Identifier: MIT

This module stores a simple mapping between Clockify project IDs and tag IDs.

Rationale: history-based tag inference is great when data exists, but for new
projects we want a deterministic 1:1 mapping.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def _map_path() -> Path:
    return Path.home() / ".config" / "clocky" / "tag-map.json"


@dataclass(frozen=True)
class TagMap:
    """Project→Tag mapping persisted on disk."""

    project_to_tag: dict[str, str]

    @classmethod
    def load(cls) -> TagMap:
        """Load mapping from disk."""
        path = _map_path()
        if not path.exists():
            return cls(project_to_tag={})
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return cls(project_to_tag={})
        if not isinstance(data, dict):
            return cls(project_to_tag={})
        project_to_tag = {str(k): str(v) for k, v in data.items()}
        return cls(project_to_tag=project_to_tag)

    def get(self, project_id: str) -> str | None:
        """Get mapped tag id for a project."""
        return self.project_to_tag.get(project_id)

    def set(self, project_id: str, tag_id: str) -> TagMap:
        """Return a new TagMap with a mapping added."""
        updated = dict(self.project_to_tag)
        updated[project_id] = tag_id
        return TagMap(project_to_tag=updated)

    def save(self) -> None:
        """Persist mapping to disk."""
        path = _map_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.project_to_tag, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            path.chmod(0o600)
        except PermissionError:
            # Best-effort on systems that do not support chmod.
            pass


def tag_map_path() -> Path:
    """Return the path to the persisted tag map file."""
    return _map_path()
