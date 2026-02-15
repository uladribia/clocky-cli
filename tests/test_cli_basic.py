"""Basic CLI smoke tests.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from typer.testing import CliRunner

import clocky.cli as cli


def test_help_works() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "start" in result.output
    assert "tag-map" in result.output
