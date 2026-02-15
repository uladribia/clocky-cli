"""Tests for display helpers.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from clocky.display import format_duration
from clocky.models import TimeEntry, TimeInterval


def test_format_duration() -> None:
    assert format_duration(timedelta(seconds=0)) == "0h 0m 0s"
    assert format_duration(timedelta(seconds=3661)) == "1h 1m 1s"


def test_time_entry_duration_running_uses_duration_string() -> None:
    interval = TimeInterval(start=datetime.now(UTC), end=None, duration="PT1H")
    entry = TimeEntry(
        id="e1",
        description="",
        projectId=None,  # type: ignore[call-arg]
        workspaceId="ws",
        userId="u",
        timeInterval=interval,
        tagIds=[],
    )

    # Private helper is exercised via print_time_entries in other tests;
    # here we just ensure the model accepts running interval.
    assert entry.time_interval.duration == "PT1H"
