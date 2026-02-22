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
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )
        config = {
            "dependency": {
                "whisper_cli": "/nonexistent/path",
                "whisper_model": "/nonexistent/model",
            },
        }
        assert app._deps_ok(config) is False


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
