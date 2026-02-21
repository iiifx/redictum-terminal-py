"""Tests for RedictumApp: initialization checks."""
from __future__ import annotations

from collections import namedtuple
from pathlib import Path

import pytest

_VersionInfo = namedtuple("version_info", "major minor micro releaselevel serial")


@pytest.fixture()
def app(tmp_path):
    from redictum import RedictumApp

    return RedictumApp(tmp_path)


class TestIsInitialized:
    """RedictumApp._is_initialized: marker file presence."""

    def test_marker_exists(self, app, tmp_path):
        (tmp_path / ".initialized").write_text("ok")
        assert app._is_initialized() is True

    def test_marker_missing(self, app):
        assert app._is_initialized() is False


class TestDepsOk:
    """RedictumApp._deps_ok: silent dependency check."""

    def test_all_present(self, app, monkeypatch, tmp_path):
        import sys

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")

        # shutil.which returns a path for all known tools
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")

        # dpkg check for build-essential
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )

        # whisper cli and model exist
        cli = tmp_path / "whisper-cli"
        model = tmp_path / "model.bin"
        cli.write_text("x")
        model.write_text("x")

        config = {
            "dependency": {
                "whisper": {
                    "cli": str(cli),
                    "model": str(model),
                },
            },
            "audio": {
                "recording": {
                    "device": "pulse",
                },
            },
        }
        assert app._deps_ok(config) is True

    def test_missing_python(self, app, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 8, 0, "final", 0))
        config = {"dependency": {"whisper": {"cli": "", "model": ""}}}
        assert app._deps_ok(config) is False

    def test_missing_whisper(self, app, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )
        config = {
            "dependency": {
                "whisper": {
                    "cli": "/nonexistent/path",
                    "model": "/nonexistent/model",
                },
            },
        }
        assert app._deps_ok(config) is False
