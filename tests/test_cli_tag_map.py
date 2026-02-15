"""Tests for tag-map CLI.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typer.testing import CliRunner

import clocky.cli as cli


def test_tag_map_help_available() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.app, ["tag-map", "--help"])
    assert result.exit_code == 0
    assert "Manage the persisted project" in result.output
