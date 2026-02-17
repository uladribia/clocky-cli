# SPDX-License-Identifier: MIT
"""Tests for `clocky tag-map pick`.

SPDX-License-Identifier: MIT

We patch questionary and build_context so the command runs fully offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import clocky.cli as cli
import clocky.cli_tag_map as cli_tag_map
from clocky.context import AppContext
from clocky.tag_map import TagMap
from clocky.testing import MOCK_PROJECTS, MOCK_TAGS, MockClockifyAPI


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_tag_map_pick_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner: CliRunner
) -> None:
    # Isolate home so the mapping file goes to a temporary directory.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    # Build an offline context using MockClockifyAPI.
    api = MockClockifyAPI()
    user = api.get_user()
    ctx = AppContext(api=api, user=user, workspace_id=user.default_workspace)
    monkeypatch.setattr(cli, "build_context", lambda: ctx)
    monkeypatch.setattr(cli_tag_map, "build_context", lambda: ctx)

    # Stateful prompt: first call → project query, second → tag query.
    prompts = iter(["Website", "bill"])
    monkeypatch.setattr(cli_tag_map.typer, "prompt", lambda *_a, **_k: next(prompts))

    # Stateful questionary.select: first call picks the project, second picks the tag.
    select_calls = [0]

    class _Sel:
        def __init__(self, value: object) -> None:
            self._value = value

        def ask(self) -> object:
            return self._value

    def _mock_select(*_args: object, **_kwargs: object) -> _Sel:
        select_calls[0] += 1
        return _Sel(MOCK_PROJECTS[0] if select_calls[0] == 1 else MOCK_TAGS[0])

    monkeypatch.setattr(cli_tag_map.questionary, "select", _mock_select)

    result = runner.invoke(cli.app, ["tag-map", "pick"])
    assert result.exit_code == 0

    m = TagMap.load()
    assert m.get(MOCK_PROJECTS[0].id) == MOCK_TAGS[0].id
