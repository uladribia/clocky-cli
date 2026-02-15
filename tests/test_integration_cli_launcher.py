"""Integration tests for the installed CLI.

SPDX-License-Identifier: MIT

These tests ensure the `clocky` executable works end-to-end in a real environment,
including fuzzy search in non-interactive mode.

They are skipped by default. Run with:

  RUN_INTEGRATION=true uv run pytest tests/test_integration_cli_launcher.py -v

Requirements:
- A valid config in ~/.config/clocky/.env (recommended) or project .env
- Network access to Clockify API

The test will:
1) Start a timer using a misspelled project name (non-interactive fuzzy)
2) Stop the running timer
3) Delete the created time entry

It also writes a small launcher-style log file into the repo under logs/.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "true",
    reason="Integration tests skipped. Set RUN_INTEGRATION=true to run.",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _log_path() -> Path:
    return _repo_root() / "logs" / "integration-launcher.log"


def _log(line: str) -> None:
    log_path = _log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    max_bytes = 200_000
    if log_path.exists() and log_path.stat().st_size > max_bytes:
        data = log_path.read_bytes()[-max_bytes // 2 :]
        log_path.write_bytes(data)

    log_path.open("a", encoding="utf-8").write(line + "\n")


def _run_clocky(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = ["clocky", *args]
    _log(f"RUN: {' '.join(cmd)}")
    proc = subprocess.run(cmd, text=True, capture_output=True)
    _log(f"exit={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


class TestInstalledClockyCLI:
    def test_start_stop_delete_with_misspelling(self) -> None:
        # Ensure clocky exists
        which = subprocess.run(["bash", "-lc", "command -v clocky"], capture_output=True, text=True)
        assert which.returncode == 0, "clocky executable not found in PATH"

        # Start timer using misspelled project name
        start = _run_clocky(
            "start",
            "--non-interactive",
            "Cros-seling",
            "--description",
            "[TEST] misspelled start via installed CLI",
        )
        assert start.returncode == 0, start.stderr

        # Get running entry id
        status = _run_clocky("status")
        assert status.returncode == 0

        # Stop
        stop = _run_clocky("stop")
        assert stop.returncode == 0

        # Find the last created entry id from `list` output (most recent first)
        # We rely on description marker to identify it.
        entries = _run_clocky("list", "--limit", "5")
        assert entries.returncode == 0

        # Delete entry via API directly to keep things clean.
        # Use same .env logic as other integration test.
        from dotenv import dotenv_values

        from clocky.api import ClockifyAPI

        env_path = _repo_root() / ".env"
        values = dotenv_values(env_path) if env_path.exists() else {}
        api_key = values.get("CLOCKIFY_API_KEY") or os.getenv("CLOCKIFY_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            pytest.skip("No API key available for cleanup")

        api = ClockifyAPI(api_key=api_key)
        user = api.get_user()
        ws = user.default_workspace

        recent = api.get_time_entries(ws, user.id, limit=10)
        target = next(
            (e for e in recent if "[TEST] misspelled start" in (e.description or "")), None
        )
        assert target is not None, "Could not find created test entry for cleanup"

        api.delete_time_entry(ws, target.id)

        recent_after = api.get_time_entries(ws, user.id, limit=10)
        assert all(e.id != target.id for e in recent_after)
