"""Tests for tag map persistence.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from pathlib import Path

from clocky.tag_map import TagMap, tag_map_path


def test_tag_map_empty_load(monkeypatch: __import__("pytest").MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    m = TagMap.load()
    assert m.project_to_tag == {}


def test_tag_map_save_and_load(
    monkeypatch: __import__("pytest").MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    m = TagMap(project_to_tag={}).set("p1", "t1").set("p2", "t2")
    m.save()

    path = tag_map_path()
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"p1": "t1", "p2": "t2"}

    loaded = TagMap.load()
    assert loaded.get("p1") == "t1"
    assert loaded.get("missing") is None
