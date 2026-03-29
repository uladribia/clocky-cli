"""Tests for shell launcher scripts.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def launcher_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Create a fake desktop environment for launcher script tests."""
    repo_root = Path(__file__).resolve().parent.parent
    home_dir = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    state_dir = home_dir / ".local" / "state" / "clocky"
    share_dir = home_dir / ".local" / "share" / "clocky"
    notifications_log = tmp_path / "notifications.log"
    clocky_calls = tmp_path / "clocky_calls.log"
    zenity_queue = tmp_path / "zenity_queue.txt"
    zenity_calls = tmp_path / "zenity_calls.log"

    bin_dir.mkdir(parents=True)
    state_dir.mkdir(parents=True)
    share_dir.mkdir(parents=True)

    for script_name in ("clocky-launcher.sh", "clocky-stop.sh", "clocky-dispatch.sh", "lib.sh"):
        shutil.copy2(repo_root / "launchers" / script_name, share_dir / script_name)

    notify_send = bin_dir / "notify-send"
    notify_send.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\n\' "$*" >>"$NOTIFY_LOG"\n',
        encoding="utf-8",
    )
    notify_send.chmod(0o755)

    zenity = bin_dir / "zenity"
    zenity.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\n\' "$*" >>"$ZENITY_CALLS"\n'
        'if [[ "${1:-}" == "--entry" ]]; then\n'
        '  if [[ ! -s "$ZENITY_QUEUE_FILE" ]]; then\n'
        "    exit 1\n"
        "  fi\n"
        '  IFS= read -r first_line <"$ZENITY_QUEUE_FILE"\n'
        "  printf '%s\n' \"$first_line\"\n"
        '  tail -n +2 "$ZENITY_QUEUE_FILE" >"$ZENITY_QUEUE_FILE.tmp" 2>/dev/null || :\n'
        '  mv "$ZENITY_QUEUE_FILE.tmp" "$ZENITY_QUEUE_FILE" 2>/dev/null || :\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    zenity.chmod(0o755)

    clocky = bin_dir / "clocky"
    clocky.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\n\' "$*" >>"$CLOCKY_CALLS"\n'
        "mode=${CLOCKY_STUB_MODE:-success}\n"
        'if [[ "${1:-}" == "start" ]]; then\n'
        '  if [[ "$mode" == "missing_tag_then_success" && "$*" != *"--tag"* ]]; then\n'
        "    printf 'Project: Brokerages\\nCLOCKY_ERROR_MISSING_TAG_MAP\\n' >&2\n"
        "    exit 1\n"
        "  fi\n"
        "  printf 'Project: Cross-selling\\n'\n"
        "  printf 'Tag: Comercial\\n\\n✔ Timer started  (id: entry-123)\\n'\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "stop" ]]; then\n'
        '  if [[ "$mode" == "no_timer" ]]; then\n'
        "    printf 'No timer is currently running.\\n' >&2\n"
        "    exit 1\n"
        "  fi\n"
        "  printf '\\n✔ Timer stopped. Duration: 0h 2m 0s\\n'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    clocky.chmod(0o755)

    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home_dir),
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "NOTIFY_LOG": str(notifications_log),
            "CLOCKY_CALLS": str(clocky_calls),
            "ZENITY_QUEUE_FILE": str(zenity_queue),
            "ZENITY_CALLS": str(zenity_calls),
            "CLOCKY_CONF_FILE": str(share_dir / "clocky.conf"),
        }
    )

    monkeypatch.setenv("HOME", str(home_dir))

    return env


def test_clocky_launcher_retries_on_missing_tag(
    launcher_env: dict[str, str], tmp_path: Path
) -> None:
    queue_file = Path(launcher_env["ZENITY_QUEUE_FILE"])
    queue_file.write_text("hoke\nComercial\n", encoding="utf-8")
    launcher = Path(launcher_env["HOME"]) / ".local" / "share" / "clocky" / "clocky-launcher.sh"
    launcher_env["CLOCKY_STUB_MODE"] = "missing_tag_then_success"

    result = subprocess.run([str(launcher)], text=True, capture_output=True, env=launcher_env)

    assert result.returncode == 0, result.stderr
    calls = Path(launcher_env["CLOCKY_CALLS"]).read_text(encoding="utf-8")
    assert "start --non-interactive hoke" in calls
    assert "start --non-interactive hoke --tag Comercial" in calls
    notifications = Path(launcher_env["NOTIFY_LOG"]).read_text(encoding="utf-8")
    assert "Timer started: Cross-selling" in notifications
    assert "Tag: Comercial" in notifications


def test_clocky_stop_launcher_reports_full_duration(launcher_env: dict[str, str]) -> None:
    launcher = Path(launcher_env["HOME"]) / ".local" / "share" / "clocky" / "clocky-stop.sh"

    result = subprocess.run([str(launcher)], text=True, capture_output=True, env=launcher_env)

    assert result.returncode == 0, result.stderr
    notifications = Path(launcher_env["NOTIFY_LOG"]).read_text(encoding="utf-8")
    assert "Timer stopped" in notifications
    assert "Duration: 0h 2m 0s" in notifications


def test_clocky_dispatch_start_with_description(launcher_env: dict[str, str]) -> None:
    queue_file = Path(launcher_env["ZENITY_QUEUE_FILE"])
    queue_file.write_text("Sprint planning\n", encoding="utf-8")
    dispatcher = Path(launcher_env["HOME"]) / ".local" / "share" / "clocky" / "clocky-dispatch.sh"

    result = subprocess.run(
        [str(dispatcher), "start", "Cross-selling"],
        text=True,
        capture_output=True,
        env=launcher_env,
    )

    assert result.returncode == 0, result.stderr
    calls = Path(launcher_env["CLOCKY_CALLS"]).read_text(encoding="utf-8")
    assert "start Cross-selling --description Sprint planning" in calls
