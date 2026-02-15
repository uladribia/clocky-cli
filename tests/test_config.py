"""Tests for configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from clocky.config import (
    CLOCKIFY_API_KEY_URL,
    Settings,
    _find_env_file,
    _open_browser,
    load_settings,
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear CLOCKIFY_* env vars to prevent leakage."""
    monkeypatch.delenv("CLOCKIFY_API_KEY", raising=False)
    monkeypatch.delenv("CLOCKIFY_WORKSPACE_ID", raising=False)


@pytest.mark.usefixtures("clean_env")
class TestSettings:
    """Tests for Settings validation."""

    def test_valid_key(self) -> None:
        s = Settings(clockify_api_key="real-key")
        assert s.clockify_api_key == "real-key"

    def test_strips_whitespace(self) -> None:
        s = Settings(clockify_api_key="  abc123  ")
        assert s.clockify_api_key == "abc123"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(clockify_api_key="")

    def test_blank_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(clockify_api_key="   ")

    def test_placeholder_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(clockify_api_key="your_api_key_here")

    def test_workspace_default(self) -> None:
        s = Settings(clockify_api_key="key")
        assert s.clockify_workspace_id == ""

    def test_workspace_set(self) -> None:
        s = Settings(clockify_api_key="key", clockify_workspace_id="ws-1")
        assert s.clockify_workspace_id == "ws-1"


@pytest.mark.usefixtures("clean_env")
class TestFindEnvFile:
    """Tests for _find_env_file()."""

    def test_finds_in_cwd(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("CLOCKIFY_API_KEY=test\n")
        original = Path.cwd()
        os.chdir(tmp_path)
        try:
            assert _find_env_file() == tmp_path / ".env"
        finally:
            os.chdir(original)

    def test_returns_xdg_default_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Remove global config to test default behavior
        xdg_env = Path.home() / ".config" / "clocky" / ".env"
        home_env = Path.home() / ".clocky.env"

        original = Path.cwd()
        os.chdir(tmp_path)
        try:
            # Temporarily rename existing configs if they exist
            xdg_backup = None
            home_backup = None
            if xdg_env.exists():
                xdg_backup = xdg_env.with_suffix(".bak")
                xdg_env.rename(xdg_backup)
            if home_env.exists():
                home_backup = home_env.with_suffix(".bak")
                home_env.rename(home_backup)

            try:
                found = _find_env_file()
                # Should return XDG config location as default
                assert found == xdg_env
            finally:
                # Restore backups
                if xdg_backup and xdg_backup.exists():
                    xdg_backup.rename(xdg_env)
                if home_backup and home_backup.exists():
                    home_backup.rename(home_env)
        finally:
            os.chdir(original)


@pytest.mark.usefixtures("clean_env")
class TestOpenBrowser:
    """Tests for _open_browser()."""

    def test_tries_xdg_open(self) -> None:
        with patch("subprocess.run") as mock_run:
            _open_browser(CLOCKIFY_API_KEY_URL)
            mock_run.assert_called_once()
            assert "xdg-open" in mock_run.call_args[0][0]

    def test_fallback_webbrowser(self) -> None:
        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch("webbrowser.open") as mock_wb,
        ):
            _open_browser(CLOCKIFY_API_KEY_URL)
            mock_wb.assert_called_once_with(CLOCKIFY_API_KEY_URL)


@pytest.mark.usefixtures("clean_env")
class TestLoadSettings:
    """Tests for load_settings()."""

    def test_exits_no_file(self, tmp_path: Path) -> None:
        # Remove global configs temporarily to test "no file" behavior
        xdg_env = Path.home() / ".config" / "clocky" / ".env"
        home_env = Path.home() / ".clocky.env"

        original = Path.cwd()
        os.chdir(tmp_path)
        try:
            xdg_backup = None
            home_backup = None
            if xdg_env.exists():
                xdg_backup = xdg_env.with_suffix(".bak")
                xdg_env.rename(xdg_backup)
            if home_env.exists():
                home_backup = home_env.with_suffix(".bak")
                home_env.rename(home_backup)

            try:
                with (
                    patch("clocky.config._show_setup_guide"),
                    pytest.raises(SystemExit) as exc,
                ):
                    load_settings()
                assert exc.value.code == 1
            finally:
                if xdg_backup and xdg_backup.exists():
                    xdg_backup.rename(xdg_env)
                if home_backup and home_backup.exists():
                    home_backup.rename(home_env)
        finally:
            os.chdir(original)

    def test_exits_placeholder(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("CLOCKIFY_API_KEY=your_api_key_here\n")
        original = Path.cwd()
        os.chdir(tmp_path)
        try:
            with (
                patch("clocky.config._show_setup_guide"),
                pytest.raises(SystemExit),
            ):
                load_settings()
        finally:
            os.chdir(original)

    def test_exits_missing_key(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("CLOCKIFY_WORKSPACE_ID=ws-1\n")
        original = Path.cwd()
        os.chdir(tmp_path)
        try:
            with (
                patch("clocky.config._show_setup_guide"),
                pytest.raises(SystemExit),
            ):
                load_settings()
        finally:
            os.chdir(original)

    def test_loads_valid(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("CLOCKIFY_API_KEY=valid-key\n")
        original = Path.cwd()
        os.chdir(tmp_path)
        try:
            settings = load_settings()
            assert settings.clockify_api_key == "valid-key"
        finally:
            os.chdir(original)
