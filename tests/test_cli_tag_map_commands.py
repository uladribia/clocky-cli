"""Tests for tag-map command behaviors beyond help and pick.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import clocky.cli.main as cli
import clocky.cli.tag_map as cli_tag_map
from clocky.infra.context import AppContext
from clocky.infra.tag_map import TagMap
from clocky.testing import MOCK_PROJECTS, MOCK_TAGS, MockClockifyAPI


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def offline_ctx() -> AppContext:
    api = MockClockifyAPI()
    user = api.get_user()
    return AppContext(api=api, user=user, workspace_id=user.default_workspace)


def test_tag_map_show_resolves_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    runner: CliRunner,
    offline_ctx: AppContext,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    TagMap(project_to_tag={MOCK_PROJECTS[0].id: MOCK_TAGS[0].id}).save()
    monkeypatch.setattr(cli, "build_context", lambda: offline_ctx)
    monkeypatch.setattr(cli_tag_map, "build_context", lambda: offline_ctx)

    result = runner.invoke(cli.app, ["tag-map", "show"])

    assert result.exit_code == 0
    payload = json.loads(result.output.split("\n\nPath:", 1)[0])
    assert payload == {MOCK_PROJECTS[0].name: MOCK_TAGS[0].name}


def test_tag_map_edit_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner: CliRunner
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(cli_tag_map.typer, "edit", lambda _text: "not-json")

    result = runner.invoke(cli.app, ["tag-map", "edit"])

    assert result.exit_code != 0
    assert "Invalid JSON" in result.output


def test_tag_map_set_and_remove_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    runner: CliRunner,
    offline_ctx: AppContext,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(cli, "build_context", lambda: offline_ctx)
    monkeypatch.setattr(cli_tag_map, "build_context", lambda: offline_ctx)

    set_result = runner.invoke(
        cli.app,
        ["tag-map", "set", MOCK_PROJECTS[0].id, MOCK_TAGS[0].id],
    )
    assert set_result.exit_code == 0
    assert TagMap.load().get(MOCK_PROJECTS[0].id) == MOCK_TAGS[0].id

    remove_result = runner.invoke(cli.app, ["tag-map", "remove", MOCK_PROJECTS[0].id])
    assert remove_result.exit_code == 0
    assert TagMap.load().get(MOCK_PROJECTS[0].id) is None
