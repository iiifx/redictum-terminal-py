"""Tests for Diagnostics."""
from __future__ import annotations

import sys
from collections import namedtuple
from pathlib import Path

import pytest

_VersionInfo = namedtuple("version_info", "major minor micro releaselevel serial")


@pytest.fixture()
def make_diagnostics(tmp_path):
    """Factory for Diagnostics with a mocked config."""

    def _make(config=None):
        from redictum import ConfigManager, Diagnostics

        if config is None:
            config = {"dependency": {"whisper_cli": "", "whisper_model": ""}}
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
        missing = diag._find_missing_apt()
        assert missing == []

    def test_some_missing(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: None)
        missing = diag._find_missing_apt()
        assert len(missing) > 0
        assert "xclip" in missing


class TestInstallAptValidation:
    """Diagnostics._install_apt: package name validation."""

    def test_valid_packages_accepted(self, make_diagnostics, monkeypatch):
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "subprocess.run", lambda cmd, **kw: MagicMock(returncode=0),
        )
        diag = make_diagnostics()
        assert diag._install_apt(["xclip"]) is True
        assert diag._install_apt(["python3-pynput"]) is True
        assert diag._install_apt(["build-essential"]) is True

    def test_malicious_name_rejected(self, make_diagnostics, monkeypatch):
        from unittest.mock import MagicMock
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)
        diag = make_diagnostics()
        assert diag._install_apt(["xclip; rm -rf /"]) is False
        mock_run.assert_not_called()

    def test_empty_name_rejected(self, make_diagnostics, monkeypatch):
        from unittest.mock import MagicMock
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)
        diag = make_diagnostics()
        assert diag._install_apt([""]) is False
        mock_run.assert_not_called()

    def test_uppercase_rejected(self, make_diagnostics, monkeypatch):
        from unittest.mock import MagicMock
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)
        diag = make_diagnostics()
        assert diag._install_apt(["Xclip"]) is False
        mock_run.assert_not_called()


class TestFindMissingPip:
    """Diagnostics._find_missing_pip: mock __import__."""

    def test_all_present(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        # All imports succeed (they're already installed in venv)
        missing = diag._find_missing_pip()
        assert missing == []


class TestConfirm:
    """Module-level _confirm: y/n input handling."""

    def test_yes(self, monkeypatch):
        from redictum import _confirm
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert _confirm("Install? ") is True

    def test_no(self, monkeypatch):
        from redictum import _confirm
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert _confirm("Install? ") is False

    def test_empty_default_false(self, monkeypatch):
        from redictum import _confirm
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert _confirm("Install?") is False

    def test_empty_default_true(self, monkeypatch):
        from redictum import _confirm
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert _confirm("Install?", default=True) is True

    def test_explicit_no_overrides_default_true(self, monkeypatch):
        from redictum import _confirm
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert _confirm("Install?", default=True) is False

    def test_eof(self, monkeypatch):
        from redictum import _confirm

        def raise_eof(_):
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        assert _confirm("Install?") is False


class TestCheckWhisper:
    """Diagnostics.check_whisper: file existence checks."""

    def test_both_exist(self, make_diagnostics, tmp_path, monkeypatch):
        cli = tmp_path / "whisper-cli"
        model = tmp_path / "model.bin"
        cli.write_text("x")
        model.write_text("x")
        config = {
            "dependency": {
                "whisper_cli": str(cli),
                "whisper_model": str(model),
            },
        }
        diag = make_diagnostics(config)
        diag.check_whisper()  # should not prompt

    def test_missing_prompts_user(self, make_diagnostics, monkeypatch):
        diag = make_diagnostics()
        monkeypatch.setattr("builtins.input", lambda _: "n")
        diag.check_whisper()  # should ask but user says no


class TestRunOptionalConfigAware:
    """run_optional(force=False) skips features disabled in config."""

    def test_all_disabled_no_prompts(self, make_diagnostics, monkeypatch):
        """When all optional features are disabled, zero prompts are shown."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "notification": {
                "sound_signal_start": False,
                "sound_signal_processing": False,
                "sound_signal_done": False,
                "sound_signal_error": False,
            },
            "audio": {"recording_normalize": False},
            "clipboard": {"paste_auto": False},
        }
        diag = make_diagnostics(config)
        # All tools missing — but config says disabled, so no prompts
        monkeypatch.setattr("shutil.which", lambda x: None)
        # If a prompt fires, input() will raise to fail the test
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(
            AssertionError("unexpected prompt"),
        ))
        diag.run_optional()  # should not raise

    def test_sound_disabled_skips_paplay(self, make_diagnostics, monkeypatch):
        """When all sound signals are disabled, paplay check is skipped."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "notification": {
                "sound_signal_start": False,
                "sound_signal_processing": False,
                "sound_signal_done": False,
                "sound_signal_error": False,
            },
            "audio": {"recording_normalize": True},
            "clipboard": {"paste_auto": True},
        }
        diag = make_diagnostics(config)
        # paplay missing, ffmpeg/xdotool present
        present = {"ffmpeg", "xdotool"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        diag.run_optional()  # paplay skipped, others pass

    def test_normalize_disabled_skips_ffmpeg(self, make_diagnostics, monkeypatch):
        """When recording_normalize is False, ffmpeg check is skipped."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "notification": {
                "sound_signal_start": True,
            },
            "audio": {"recording_normalize": False},
            "clipboard": {"paste_auto": True},
        }
        diag = make_diagnostics(config)
        # ffmpeg missing, paplay/xdotool present
        present = {"paplay", "xdotool"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        diag.run_optional()  # ffmpeg skipped, others pass

    def test_paste_disabled_skips_xdotool(self, make_diagnostics, monkeypatch):
        """When paste_auto is False, xdotool check is skipped."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "notification": {
                "sound_signal_start": True,
            },
            "audio": {"recording_normalize": True},
            "clipboard": {"paste_auto": False},
        }
        diag = make_diagnostics(config)
        # xdotool missing, paplay/ffmpeg present
        present = {"paplay", "ffmpeg"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        diag.run_optional()  # xdotool skipped, others pass
