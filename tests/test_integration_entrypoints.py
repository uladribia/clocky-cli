"""Tests for smoke-test entrypoint robustness.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os
import subprocess

from typer.testing import CliRunner

import clocky.cli.main as cli


def test_integration_test_help_includes_plan() -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["integration-test", "--help"])

    assert result.exit_code == 0
    assert "--plan" in result.output


def test_integration_test_sets_module_entrypoint_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("CLOCKY_INTEGRATION_CLI", raising=False)
    monkeypatch.setattr(cli, "run_integration_smoke", lambda _cases, _limit: 0)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["integration-test", "--case", "status_json"])

    assert result.exit_code == 0
    assert os.environ["CLOCKY_INTEGRATION_CLI"].endswith(" -m clocky.cli")


def test_script_plan_entrypoint_runs_from_python(tmp_path) -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/integration_smoke.py", "--plan"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "start_stop project:" in result.stdout
    assert "missing_tag project:" in result.stdout
