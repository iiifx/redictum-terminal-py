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

        # whisper cli and model exist
        cli = tmp_path / "whisper-cli"
        model = tmp_path / "model.bin"
        cli.write_text("x")
        model.write_text("x")

        config = {
            "dependency": {
                "whisper_cli": str(cli),
                "whisper_model": str(model),
            },
            "audio": {
                "recording_device": "pulse",
            },
        }
        assert app._deps_ok(config) is True

    def test_missing_python(self, app, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 8, 0, "final", 0))
        config = {"dependency": {"whisper_cli": "", "whisper_model": ""}}
        assert app._deps_ok(config) is False

    def test_missing_whisper(self, app, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        config = {
            "dependency": {
                "whisper_cli": "/nonexistent/path",
                "whisper_model": "/nonexistent/model",
            },
        }
        assert app._deps_ok(config) is False


class TestCollectMissingDeps:
    """RedictumApp._collect_missing_deps: list missing runtime deps."""

    def test_all_present(self, app, tmp_path, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
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
        assert app._collect_missing_deps(config) == []

    def test_missing_apt(self, app, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: None)
        config = {"dependency": {"whisper_cli": "", "whisper_model": ""}}
        missing = app._collect_missing_deps(config)
        assert "xclip" in missing

    def test_xclip_present_not_in_missing(self, app, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        config = {"dependency": {"whisper_cli": "", "whisper_model": ""}}
        missing = app._collect_missing_deps(config)
        assert "xclip" not in missing

    def test_missing_whisper(self, app, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        config = {
            "dependency": {
                "whisper_cli": "/nonexistent/cli",
                "whisper_model": "/nonexistent/model",
            },
        }
        missing = app._collect_missing_deps(config)
        assert "whisper.cpp" in missing
        assert "whisper model" in missing

    def test_empty_whisper_paths(self, app, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        config = {"dependency": {"whisper_cli": "", "whisper_model": ""}}
        missing = app._collect_missing_deps(config)
        assert "whisper.cpp" in missing
        assert "whisper model" in missing


class TestInitAbort:
    """init() aborts when user declines critical deps."""

    def test_init_raises_when_deps_missing(self, app, monkeypatch, tmp_path):
        """init() raises RedictumError when runtime deps are not satisfied."""
        import sys
        from unittest.mock import MagicMock
        from redictum import RedictumError

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")
        # Stage 1 tools present, but xclip missing (critical dep)
        stage1_tools = {"arecord", "apt"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in stage1_tools else None,
        )
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )
        # User declines install
        monkeypatch.setattr("builtins.input", lambda _: "n")

        with pytest.raises(RedictumError, match="Setup incomplete"):
            app.init()

        # .initialized should NOT exist
        assert not (tmp_path / ".initialized").exists()

    def test_init_aborts_before_whisper_when_core_missing(self, app, monkeypatch, tmp_path):
        """init() aborts after stage2 without asking about whisper."""
        import sys
        from unittest.mock import MagicMock, call, patch
        from redictum import RedictumError

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")
        # xclip missing → critical dep failure before whisper check
        stage1_tools = {"arecord", "apt"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in stage1_tools else None,
        )
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )
        monkeypatch.setattr("builtins.input", lambda _: "n")

        # Spy on check_whisper to verify it's never called
        from redictum import Diagnostics
        with patch.object(Diagnostics, "check_whisper") as mock_whisper:
            with pytest.raises(RedictumError, match="Setup incomplete"):
                app.init()
            mock_whisper.assert_not_called()

    def test_init_marks_initialized_when_deps_ok(self, app, monkeypatch, tmp_path):
        """init() writes .initialized when all deps are satisfied."""
        import sys
        from unittest.mock import MagicMock

        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )

        # Create whisper files so check_whisper passes
        cli = tmp_path / "whisper-cli"
        model = tmp_path / "model.bin"
        cli.write_text("x")
        model.write_text("x")

        # Write config with whisper paths
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[dependency]\n"
            f'whisper_cli = "{cli}"\n'
            f'whisper_model = "{model}"\n'
        )

        app.init()
        assert (tmp_path / ".initialized").exists()


class TestApplyOverrides:
    """_apply_overrides: --set section.key=value CLI overrides."""

    def test_string_override(self):
        from redictum import _apply_overrides

        config = {"dependency": {"whisper_language": "auto"}}
        _apply_overrides(config, ["dependency.whisper_language=en"])
        assert config["dependency"]["whisper_language"] == "en"

    def test_int_override(self):
        from redictum import _apply_overrides

        config = {"dependency": {"whisper_timeout": 120}}
        _apply_overrides(config, ["dependency.whisper_timeout=60"])
        assert config["dependency"]["whisper_timeout"] == 60

    def test_bool_override_true(self):
        from redictum import _apply_overrides

        config = {"audio": {"recording_normalize": False}}
        _apply_overrides(config, ["audio.recording_normalize=true"])
        assert config["audio"]["recording_normalize"] is True

    def test_bool_override_false(self):
        from redictum import _apply_overrides

        config = {"audio": {"recording_normalize": True}}
        _apply_overrides(config, ["audio.recording_normalize=off"])
        assert config["audio"]["recording_normalize"] is False

    def test_float_override(self):
        from redictum import _apply_overrides

        config = {"input": {"hotkey_hold_delay": 0.6}}
        _apply_overrides(config, ["input.hotkey_hold_delay=0.3"])
        assert config["input"]["hotkey_hold_delay"] == pytest.approx(0.3)

    def test_paste_restore_delay_override(self):
        from redictum import _apply_overrides

        config = {"clipboard": {"paste_restore_delay": 0.3}}
        _apply_overrides(config, ["clipboard.paste_restore_delay=0.5"])
        assert config["clipboard"]["paste_restore_delay"] == pytest.approx(0.5)

    def test_quoted_string_stripped(self):
        from redictum import _apply_overrides

        config = {"dependency": {"whisper_language": "auto"}}
        _apply_overrides(config, ['dependency.whisper_language="ru"'])
        assert config["dependency"]["whisper_language"] == "ru"

    def test_multiple_overrides(self):
        from redictum import _apply_overrides

        config = {
            "dependency": {"whisper_language": "auto", "whisper_timeout": 120},
        }
        _apply_overrides(config, [
            "dependency.whisper_language=en",
            "dependency.whisper_timeout=30",
        ])
        assert config["dependency"]["whisper_language"] == "en"
        assert config["dependency"]["whisper_timeout"] == 30

    def test_missing_equals_raises(self):
        from redictum import _apply_overrides, RedictumError

        with pytest.raises(RedictumError, match="Invalid --set format"):
            _apply_overrides({}, ["dependency.whisper_language"])

    def test_unknown_section_raises(self):
        from redictum import _apply_overrides, RedictumError

        with pytest.raises(RedictumError, match="Unknown section"):
            _apply_overrides({}, ["nonexistent.key=val"])

    def test_unknown_key_raises(self):
        from redictum import _apply_overrides, RedictumError

        with pytest.raises(RedictumError, match="Unknown key"):
            _apply_overrides({}, ["dependency.nonexistent_key=val"])

    def test_bad_int_raises(self):
        from redictum import _apply_overrides, RedictumError

        config = {"dependency": {"whisper_timeout": 120}}
        with pytest.raises(RedictumError, match="Invalid value"):
            _apply_overrides(config, ["dependency.whisper_timeout=abc"])

    def test_bad_float_raises(self):
        from redictum import _apply_overrides, RedictumError

        config = {"clipboard": {"paste_restore_delay": 0.3}}
        with pytest.raises(RedictumError, match="Invalid value"):
            _apply_overrides(config, ["clipboard.paste_restore_delay=slow"])


class TestCheckOptionalMismatch:
    """RedictumApp._check_optional_mismatch: detect enabled features with missing tools."""

    def test_all_tools_present(self, app, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        config = {
            "notification": {
                "sound_signal_start": True,
                "sound_signal_done": True,
                "sound_signal_error": True,
            },
            "audio": {"recording_normalize": True},
            "clipboard": {"paste_auto": True},
        }
        assert app._check_optional_mismatch(config) is False

    def test_paplay_missing_sound_enabled(self, app, monkeypatch):
        present = {"ffmpeg", "xdotool"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        config = {
            "notification": {"sound_signal_start": True},
            "audio": {"recording_normalize": True},
            "clipboard": {"paste_auto": True},
        }
        assert app._check_optional_mismatch(config) is True

    def test_ffmpeg_missing_normalize_enabled(self, app, monkeypatch):
        present = {"paplay", "xdotool"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        config = {
            "notification": {
                "sound_signal_start": False,
                "sound_signal_processing": False,
                "sound_signal_done": False,
                "sound_signal_error": False,
            },
            "audio": {"recording_normalize": True},
            "clipboard": {"paste_auto": True},
        }
        assert app._check_optional_mismatch(config) is True

    def test_xdotool_missing_paste_enabled(self, app, monkeypatch):
        present = {"paplay", "ffmpeg"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        config = {
            "notification": {
                "sound_signal_start": False,
                "sound_signal_processing": False,
                "sound_signal_done": False,
                "sound_signal_error": False,
            },
            "audio": {"recording_normalize": False},
            "clipboard": {"paste_auto": True},
        }
        assert app._check_optional_mismatch(config) is True

    def test_all_disabled_all_missing(self, app, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: None)
        config = {
            "notification": {
                "sound_signal_start": False,
                "sound_signal_processing": False,
                "sound_signal_done": False,
                "sound_signal_error": False,
            },
            "audio": {"recording_normalize": False},
            "clipboard": {"paste_auto": False},
        }
        assert app._check_optional_mismatch(config) is False
