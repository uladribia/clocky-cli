# SPDX-License-Identifier: MIT
"""Global output-mode state for --json and --quiet flags.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from clocky.models import TimeEntry


@dataclass
class OutputMode:
    """Mutable singleton holding the current output mode."""

    json: bool = False
    quiet: bool = False


_mode = OutputMode()


def get_mode() -> OutputMode:
    """Return the current output mode."""
    return _mode


def set_mode(*, json_mode: bool = False, quiet: bool = False) -> None:
    """Set the global output mode.

    Args:
        json_mode: Emit JSON to stdout instead of Rich tables.
        quiet: Suppress informational output (errors still go to stderr).

    """
    _mode.json = json_mode
    _mode.quiet = quiet


def emit_json(data: Any) -> None:
    """Write *data* as JSON to stdout and exit.

    Args:
        data: Serializable object (dict, list, etc.).

    """
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")


def time_entry_to_dict(
    entry: TimeEntry,
    *,
    project_name: str | None = None,
    tag_names: list[str] | None = None,
) -> dict[str, Any]:
    """Convert a TimeEntry to a JSON-friendly dict.

    Args:
        entry: The time entry.
        project_name: Resolved project name (optional).
        tag_names: Resolved tag names (optional).

    Returns:
        Plain dict suitable for JSON serialisation.

    """
    interval = entry.time_interval
    return {
        "id": entry.id,
        "description": entry.description,
        "project_id": entry.project_id,
        "project_name": project_name,
        "tag_ids": entry.tag_ids,
        "tag_names": tag_names or [],
        "start": interval.start.isoformat(),
        "end": interval.end.isoformat() if interval.end else None,
        "duration": interval.duration,
    }
