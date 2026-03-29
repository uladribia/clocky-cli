# SPDX-License-Identifier: MIT
"""Testing support package for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from clocky.testing.fakes import (
    MOCK_CLIENTS,
    MOCK_PROJECTS,
    MOCK_TAGS,
    MOCK_TIME_ENTRIES,
    MOCK_USER,
    MOCK_WORKSPACES,
    MockClockifyAPI,
)

__all__ = [
    "MOCK_CLIENTS",
    "MOCK_PROJECTS",
    "MOCK_TAGS",
    "MOCK_TIME_ENTRIES",
    "MOCK_USER",
    "MOCK_WORKSPACES",
    "MockClockifyAPI",
]
