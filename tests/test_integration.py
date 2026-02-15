"""Integration tests using the real Clockify API.

These tests require a valid CLOCKIFY_API_KEY in .env and will create/delete
real time entries. Run with: uv run pytest tests/test_integration.py -v

Skipped by default in normal test runs. Use --run-integration to run them.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from clocky.api import ClockifyAPI
from clocky.models import StartTimerRequest, StopTimerRequest

# Skip by default — run explicitly with: pytest tests/test_integration.py
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "true",
    reason="Integration tests skipped. Set RUN_INTEGRATION=true to run.",
)


@pytest.fixture
def api() -> ClockifyAPI:
    """Create a real API client from .env settings.

    Reads .env directly to avoid pollution from other tests.
    """
    from dotenv import dotenv_values

    # Use the same resolution as the app: repo .env OR XDG config .env
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        xdg_env = Path.home() / ".config" / "clocky" / ".env"
        if xdg_env.exists():
            env_path = xdg_env
        else:
            pytest.skip(".env file not found")

    values = dotenv_values(env_path)
    api_key = values.get("CLOCKIFY_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        pytest.skip("Valid CLOCKIFY_API_KEY not found in .env")

    return ClockifyAPI(api_key=api_key)


@pytest.fixture
def workspace_id(api: ClockifyAPI) -> str:
    """Get the user's default workspace."""
    user = api.get_user()
    return user.default_workspace


class TestRealAPI:
    """Integration tests against the live Clockify API."""

    def test_start_stop_delete_timer(self, api: ClockifyAPI, workspace_id: str) -> None:
        """Start a timer on Cross-selling/Dribia with Comercial tag, stop it, delete it.

        This test is idempotent — it cleans up after itself.
        """
        # Find the Cross-selling project
        projects = api.get_projects(workspace_id)
        cross_selling = next(
            (p for p in projects if p.name == "Cross-selling" and p.client_name == "Dribia"),
            None,
        )
        assert cross_selling is not None, "Project 'Cross-selling' for 'Dribia' not found"

        # Find the Comercial tag
        tags = api.get_tags(workspace_id)
        comercial_tag = next((t for t in tags if t.name == "Comercial"), None)
        assert comercial_tag is not None, "Tag 'Comercial' not found"

        # Start the timer
        from datetime import UTC, datetime

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        start_request = StartTimerRequest(
            start=now,
            description="[TEST] Integration test entry — will be deleted",
            project_id=cross_selling.id,
            tag_ids=[comercial_tag.id],
        )
        entry = api.start_timer(workspace_id, start_request)
        assert entry.id is not None
        assert entry.project_id == cross_selling.id
        assert comercial_tag.id in entry.tag_ids

        # Brief pause to ensure timer is running
        time.sleep(1)

        # Verify timer is running
        user = api.get_user()
        running = api.get_running_timer(workspace_id, user.id)
        assert running is not None
        assert running.id == entry.id

        # Stop the timer
        end_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        stop_request = StopTimerRequest(end=end_time)
        stopped = api.stop_timer(workspace_id, user.id, stop_request)
        assert stopped.time_interval.end is not None

        # Verify timer is no longer running
        running_after = api.get_running_timer(workspace_id, user.id)
        assert running_after is None

        # Delete the entry to keep it idempotent
        api.delete_time_entry(workspace_id, entry.id)

        # Verify deletion by checking it's not in recent entries
        recent = api.get_time_entries(workspace_id, user.id, limit=5)
        assert all(e.id != entry.id for e in recent), "Entry should have been deleted"
