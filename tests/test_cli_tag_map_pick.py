"""Tests for `clocky tag-map pick`.

SPDX-License-Identifier: MIT

We patch questionary and build_context so the command runs offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import clocky.cli as cli
from clocky.context import AppContext
from clocky.models import Project, Tag, User
from clocky.tag_map import TagMap


class _StubAPI:
    def get_projects(self, _workspace_id: str) -> list[Project]:
        return [
            Project(id="p1", name="Project Alpha", clientId=None),  # type: ignore[call-arg]
            Project(id="p2", name="Project Beta", clientId=None),  # type: ignore[call-arg]
        ]

    def get_tags(self, _workspace_id: str) -> list[Tag]:
        return [Tag(id="t1", name="Comercial", workspaceId="ws")]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_tag_map_pick_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner: CliRunner
) -> None:
    # Isolate home so mapping file goes to tmp
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    # Patch build_context
    user = User(id="u", name="N", email="e", defaultWorkspace="ws")
    # AppContext.api is typed as ClockifyAPI; for this unit test we only need get_projects/get_tags.
    ctx = AppContext(api=_StubAPI(), user=user, workspace_id="ws")  # type: ignore[arg-type]
    monkeypatch.setattr(cli, "build_context", lambda: ctx)

    # Patch prompts / questionary
    monkeypatch.setattr(cli.typer, "prompt", lambda *_args, **_kwargs: "Alpha")

    import clocky.cli_tag_map as cli_tag_map

    monkeypatch.setattr(cli_tag_map.typer, "prompt", lambda *_args, **_kwargs: "Alpha")

    class _Sel:
        def __init__(self, value):
            self._value = value

        def ask(self):
            return self._value

    monkeypatch.setattr(
        cli_tag_map.questionary, "select", lambda *_a, **_k: _Sel(_StubAPI().get_projects("ws")[0])
    )
    # second select returns tag
    monkeypatch.setattr(
        cli_tag_map.questionary,
        "select",
        lambda *_a, **_k: (
            _Sel(_StubAPI().get_projects("ws")[0])
            if "project" in _a[0].lower()
            else _Sel(_StubAPI().get_tags("ws")[0])
        ),
    )

    result = runner.invoke(cli.app, ["tag-map", "pick"])
    assert result.exit_code == 0

    m = TagMap.load()
    assert m.get("p1") == "t1"
