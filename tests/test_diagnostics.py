"""Tests for Diagnostics."""
from __future__ import annotations

import sys
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_VersionInfo = namedtuple("version_info", "major minor micro releaselevel serial")


@pytest.fixture()
def make_diagnostics(tmp_path):
    """Factory for Diagnostics with a mocked config."""

    def _make(config=None):
        from redictum import ConfigManager, Diagnostics

        if config is None:
            config = {"dependency": {"whisper": {"cli": "", "model": ""}}}
        mgr = ConfigManager(tmp_path)
        return Diagnostics(config, mgr)

    return _make


class TestCheckPython:
    """Diagnostics._check_python: version gate."""

    def test_ok_version(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        diag._check_python()  # no exception

    def test_old_version(self, make_diagnostics, monkeypatch):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 1, "final", 0))
        with pytest.raises(RedictumError, match="3.10"):
            diag._check_python()


class TestCheckLinux:
    """Diagnostics._check_linux."""

    def test_linux(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr(sys, "platform", "linux")
        diag._check_linux()

    def test_non_linux(self, make_diagnostics, monkeypatch):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.setattr(sys, "platform", "darwin")
        with pytest.raises(RedictumError, match="Linux is required"):
            diag._check_linux()


class TestCheckPulseaudio:
    """Diagnostics._check_pulseaudio."""

    def test_found(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/paplay" if x == "paplay" else None)
        diag._check_pulseaudio()

    def test_not_found(self, make_diagnostics, monkeypatch):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: None)
        with pytest.raises(RedictumError, match="PulseAudio"):
            diag._check_pulseaudio()


class TestCheckAlsa:
    """Diagnostics._check_alsa."""

    def test_found(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/arecord" if x == "arecord" else None)
        diag._check_alsa()

    def test_not_found(self, make_diagnostics, monkeypatch):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: None)
        with pytest.raises(RedictumError, match="ALSA"):
            diag._check_alsa()


class TestCheckX11:
    """Diagnostics._check_x11."""

    def test_display_set(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setenv("DISPLAY", ":0")
        diag._check_x11()

    def test_display_unset(self, make_diagnostics, monkeypatch):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.delenv("DISPLAY", raising=False)
        with pytest.raises(RedictumError, match="DISPLAY"):
            diag._check_x11()


class TestFindMissingApt:
    """Diagnostics._find_missing_apt: mock shutil.which."""

    def test_all_present(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        # build-essential check via dpkg
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )
        missing = diag._find_missing_apt()
        assert missing == []

    def test_some_missing(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        present = {"git", "cmake"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=1),
        )
        missing = diag._find_missing_apt()
        assert len(missing) > 0
        assert "git" not in missing
        assert "cmake" not in missing


class TestFindMissingPip:
    """Diagnostics._find_missing_pip: mock __import__."""

    def test_all_present(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        # All imports succeed (they're already installed in venv)
        missing = diag._find_missing_pip()
        assert missing == []


class TestConfirm:
    """Diagnostics._confirm: y/n input handling."""

    def test_yes(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert diag._confirm("Install? ") is True

    def test_no(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert diag._confirm("Install? ") is False

    def test_eof(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()

        def raise_eof(_):
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        assert diag._confirm("Install? ") is False


class TestCheckWhisper:
    """Diagnostics.check_whisper: file existence checks."""

    def test_both_exist(self, make_diagnostics, tmp_path, monkeypatch):
        cli = tmp_path / "whisper-cli"
        model = tmp_path / "model.bin"
        cli.write_text("x")
        model.write_text("x")
        config = {
            "dependency": {
                "whisper": {"cli": str(cli), "model": str(model)},
            },
        }
        diag = make_diagnostics(config)
        diag.check_whisper()  # should not prompt

    def test_missing_prompts_user(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("builtins.input", lambda _: "n")
        diag.check_whisper()  # should ask but user says no
