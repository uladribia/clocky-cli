"""Tests for interactive setup workflow.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from rich.console import Console

import clocky.setup as clocky_setup
from clocky.setup_service import (
    APIClientFactory,
    ConnectionCheckResult,
    build_env_content,
    detect_existing_config,
    verify_api_key,
)


class _RecordingConsole(Console):
    def __init__(self) -> None:
        super().__init__(record=True)


class _User:
    def __init__(self, name: str = "Test User", email: str = "test@example.com") -> None:
        self.name = name
        self.email = email


class _APIClient:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.closed = False

    def get_user(self) -> _User:
        if self.should_fail:
            raise RuntimeError("bad key")
        return _User()

    def close(self) -> None:
        self.closed = True


def test_build_env_content_includes_optional_workspace() -> None:
    assert build_env_content("key", "ws-1") == "CLOCKIFY_API_KEY=key\nCLOCKIFY_WORKSPACE_ID=ws-1\n"
    assert build_env_content("key", "") == "CLOCKIFY_API_KEY=key\n"


def test_detect_existing_config_recognises_configured_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CLOCKIFY_API_KEY=real-key\n", encoding="utf-8")

    state = detect_existing_config(env_file)

    assert state.exists is True
    assert state.configured is True


def test_verify_api_key_closes_client_on_success() -> None:
    client = _APIClient()

    def factory(_api_key: str) -> _APIClient:
        return client

    result = verify_api_key(cast(APIClientFactory, factory), "real-key")

    assert result == ConnectionCheckResult(
        success=True,
        user_name="Test User",
        user_email="test@example.com",
        error_message="",
    )
    assert client.closed is True


def test_verify_api_key_returns_error_and_closes_client() -> None:
    client = _APIClient(should_fail=True)

    def factory(_api_key: str) -> _APIClient:
        return client

    result = verify_api_key(cast(APIClientFactory, factory), "bad-key")

    assert result.success is False
    assert "bad key" in result.error_message
    assert client.closed is True


def test_setup_writes_env_and_reports_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".config" / "clocky" / ".env"
    console = _RecordingConsole()
    confirms = iter([False])
    prompts = iter(["real-key", "ws-1"])

    monkeypatch.setattr(clocky_setup.Confirm, "ask", lambda *_a, **_k: next(confirms))
    monkeypatch.setattr(clocky_setup.Prompt, "ask", lambda *_a, **_k: next(prompts))
    monkeypatch.setattr(
        clocky_setup, "open_browser", lambda _url: (_ for _ in ()).throw(AssertionError)
    )

    clocky_setup.setup(
        env_file=env_file,
        console_obj=console,
        api_factory=cast(APIClientFactory, lambda _k: _APIClient()),
    )

    assert env_file.read_text(encoding="utf-8") == (
        "CLOCKIFY_API_KEY=real-key\nCLOCKIFY_WORKSPACE_ID=ws-1\n"
    )
    output = console.export_text()
    assert "Configuration saved" in output
    assert "Setup complete" in output
    assert "Connected as: Test User" in output


def test_setup_cancels_when_existing_config_is_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CLOCKIFY_API_KEY=already-set\n", encoding="utf-8")
    console = _RecordingConsole()

    monkeypatch.setattr(clocky_setup.Confirm, "ask", lambda *_a, **_k: False)

    clocky_setup.setup(
        env_file=env_file,
        console_obj=console,
        api_factory=cast(APIClientFactory, lambda _k: _APIClient()),
    )

    output = console.export_text()
    assert "Config already exists" in output
    assert "Setup cancelled" in output
    assert env_file.read_text(encoding="utf-8") == "CLOCKIFY_API_KEY=already-set\n"


def test_setup_reports_connection_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    console = _RecordingConsole()
    confirms = iter([False])
    prompts = iter(["bad-key", ""])

    monkeypatch.setattr(clocky_setup.Confirm, "ask", lambda *_a, **_k: next(confirms))
    monkeypatch.setattr(clocky_setup.Prompt, "ask", lambda *_a, **_k: next(prompts))

    clocky_setup.setup(
        env_file=env_file,
        console_obj=console,
        api_factory=cast(APIClientFactory, lambda _k: _APIClient(should_fail=True)),
    )

    output = console.export_text()
    assert "Connection failed: bad key" in output
    assert env_file.read_text(encoding="utf-8") == "CLOCKIFY_API_KEY=bad-key\n"
