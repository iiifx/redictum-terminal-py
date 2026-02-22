"""Tests for comprehensive diagnostics logging."""
from __future__ import annotations

import logging
import sys
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_VersionInfo = namedtuple("version_info", "major minor micro releaselevel serial")


# ---------------------------------------------------------------------------
# _log_system_info
# ---------------------------------------------------------------------------

class TestLogSystemInfo:
    """_log_system_info: never crashes, logs system snapshot."""

    def test_no_crash_normal(self):
        from redictum import _log_system_info

        _log_system_info()  # should not raise

    def test_no_crash_missing_os_release(self, monkeypatch):
        from redictum import _log_system_info

        orig_read = Path.read_text

        def fake_read(self_, *a, **kw):
            if str(self_) == "/etc/os-release":
                raise FileNotFoundError
            return orig_read(self_, *a, **kw)

        monkeypatch.setattr(Path, "read_text", fake_read)
        _log_system_info()  # falls back to platform.platform()

    def test_no_crash_missing_nvidia_smi(self, monkeypatch):
        from redictum import _log_system_info

        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError),
        )
        _log_system_info()  # GPU/CUDA → N/A

    def test_no_crash_missing_proc_meminfo(self, monkeypatch):
        from redictum import _log_system_info

        orig_read = Path.read_text

        def fake_read(self_, *a, **kw):
            if str(self_) == "/proc/meminfo":
                raise FileNotFoundError
            return orig_read(self_, *a, **kw)

        monkeypatch.setattr(Path, "read_text", fake_read)
        _log_system_info()  # RAM → N/A

    def test_logs_system_line(self, caplog):
        from redictum import _log_system_info

        with caplog.at_level(logging.INFO):
            _log_system_info()

        assert any("System:" in r.message for r in caplog.records)

    def test_logs_all_fields(self, caplog):
        """System info log should contain all expected fields."""
        from redictum import _log_system_info

        with caplog.at_level(logging.INFO):
            _log_system_info()

        msg = next(r.message for r in caplog.records if "System:" in r.message)
        assert "Python:" in msg
        assert "Locale:" in msg
        assert "Display:" in msg
        assert "GPU:" in msg
        assert "CUDA:" in msg
        assert "RAM:" in msg

    def test_catastrophic_exception_logged_as_warning(self, monkeypatch, caplog):
        """If everything blows up, log a warning — never crash."""
        from redictum import _log_system_info

        # Break Path("/etc/os-release").read_text AND platform.platform
        monkeypatch.setattr("platform.platform", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        orig_read = Path.read_text

        def nuke_read(self_, *a, **kw):
            if str(self_) == "/etc/os-release":
                raise FileNotFoundError
            return orig_read(self_, *a, **kw)

        monkeypatch.setattr(Path, "read_text", nuke_read)

        with caplog.at_level(logging.WARNING):
            _log_system_info()  # should not raise

        assert any("Failed to collect system info" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _confirm logging
# ---------------------------------------------------------------------------

class TestConfirmLogging:
    """_confirm() logs prompt and user answer."""

    def test_logs_yes(self, monkeypatch, caplog):
        from redictum import _confirm

        monkeypatch.setattr("builtins.input", lambda _: "y")
        with caplog.at_level(logging.INFO):
            result = _confirm("Install?")

        assert result is True
        assert any("yes" in r.message and "Install?" in r.message for r in caplog.records)

    def test_logs_no(self, monkeypatch, caplog):
        from redictum import _confirm

        monkeypatch.setattr("builtins.input", lambda _: "n")
        with caplog.at_level(logging.INFO):
            result = _confirm("Install?")

        assert result is False
        assert any("no" in r.message and "Install?" in r.message for r in caplog.records)

    def test_logs_eof(self, monkeypatch, caplog):
        from redictum import _confirm

        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        with caplog.at_level(logging.INFO):
            result = _confirm("Install?")

        assert result is False
        assert any("no" in r.message and "Install?" in r.message for r in caplog.records)

    def test_logs_default_true(self, monkeypatch, caplog):
        """Empty input with default=True logs 'yes'."""
        from redictum import _confirm

        monkeypatch.setattr("builtins.input", lambda _: "")
        with caplog.at_level(logging.INFO):
            result = _confirm("Proceed?", default=True)

        assert result is True
        assert any("yes" in r.message and "Proceed?" in r.message for r in caplog.records)

    def test_logs_default_false(self, monkeypatch, caplog):
        """Empty input with default=False logs 'no'."""
        from redictum import _confirm

        monkeypatch.setattr("builtins.input", lambda _: "")
        with caplog.at_level(logging.INFO):
            result = _confirm("Proceed?", default=False)

        assert result is False
        assert any("no" in r.message and "Proceed?" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

class TestSetupLoggingForce:
    """setup_logging(force=True) replaces existing handlers."""

    def test_force_replaces_handlers(self, tmp_path):
        from redictum import setup_logging

        log1 = tmp_path / "logs" / "first.log"
        log2 = tmp_path / "logs" / "second.log"

        setup_logging(log1, force=True)
        logging.info("message-one")

        setup_logging(log2, force=True)
        logging.info("message-two")

        assert log2.exists()
        content2 = log2.read_text()
        assert "message-two" in content2
        # message-one should NOT be in log2
        assert "message-one" not in content2

    def test_creates_parent_dirs(self, tmp_path):
        from redictum import setup_logging

        log_path = tmp_path / "deep" / "nested" / "app.log"
        setup_logging(log_path, force=True)
        logging.info("test-mkdir")

        assert log_path.exists()
        assert "test-mkdir" in log_path.read_text()


# ---------------------------------------------------------------------------
# Diagnostics check logging
# ---------------------------------------------------------------------------

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


class TestDiagnosticsCheckLogging:
    """Verify that each Diagnostics check produces a log record."""

    def test_check_python_logs_ok(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 12, 0, "final", 0))
        with caplog.at_level(logging.INFO):
            diag._check_python()
        assert any("Check:" in r.message and "OK" in r.message for r in caplog.records)

    def test_check_python_logs_fail(self, make_diagnostics, monkeypatch, caplog):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.setattr(sys, "version_info", _VersionInfo(3, 9, 1, "final", 0))
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RedictumError):
                diag._check_python()
        assert any("FAIL" in r.message for r in caplog.records)

    def test_check_linux_logs_ok(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setattr(sys, "platform", "linux")
        with caplog.at_level(logging.INFO):
            diag._check_linux()
        assert any("Linux" in r.message and "OK" in r.message for r in caplog.records)

    def test_check_alsa_logs_ok(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/arecord" if x == "arecord" else None)
        with caplog.at_level(logging.INFO):
            diag._check_alsa()
        assert any("ALSA" in r.message and "OK" in r.message for r in caplog.records)

    def test_check_x11_logs_ok(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setenv("DISPLAY", ":0")
        with caplog.at_level(logging.INFO):
            diag._check_x11()
        assert any("X11" in r.message and ":0" in r.message for r in caplog.records)

    def test_check_x11_logs_fail(self, make_diagnostics, monkeypatch, caplog):
        from redictum import RedictumError

        diag = make_diagnostics()
        monkeypatch.delenv("DISPLAY", raising=False)
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RedictumError):
                diag._check_x11()
        assert any("X11" in r.message and "not set" in r.message for r in caplog.records)

    def test_detect_audio_device_manual_logs(self, make_diagnostics, caplog):
        config = {
            "audio": {"recording_device": "pulse"},
            "dependency": {"whisper_cli": "", "whisper_model": ""},
        }
        diag = make_diagnostics(config)
        with caplog.at_level(logging.INFO):
            diag._detect_audio_device()
        assert any("Audio device" in r.message and "manual" in r.message for r in caplog.records)


class TestDiagnosticsPackageLogging:
    """Verify that package detection produces log records."""

    def test_find_missing_apt_all_present(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        with caplog.at_level(logging.INFO):
            missing = diag._find_missing_apt()
        assert missing == []
        assert any("All apt packages present" in r.message for r in caplog.records)

    def test_find_missing_apt_some_missing(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: None)
        with caplog.at_level(logging.INFO):
            missing = diag._find_missing_apt()
        assert len(missing) > 0
        assert any("Missing apt:" in r.message for r in caplog.records)

    def test_find_missing_pip_all_present(self, make_diagnostics, caplog):
        diag = make_diagnostics()
        with caplog.at_level(logging.INFO):
            missing = diag._find_missing_pip()
        assert missing == []
        assert any("All pip packages present" in r.message for r in caplog.records)


class TestWhisperCheckLogging:
    """Verify whisper check produces log records."""

    def test_both_exist_logs(self, make_diagnostics, tmp_path, caplog):
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
        with caplog.at_level(logging.INFO):
            diag.check_whisper()
        assert any("Whisper CLI" in r.message and "found" in r.message for r in caplog.records)
        assert any("Whisper model" in r.message and "found" in r.message for r in caplog.records)

    def test_missing_logs(self, make_diagnostics, monkeypatch, caplog):
        diag = make_diagnostics()
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with caplog.at_level(logging.INFO):
            diag.check_whisper()
        assert any("Whisper CLI" in r.message and "missing" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# run_optional() checks
# ---------------------------------------------------------------------------

class TestRunOptional:
    """Diagnostics.run_optional: optional dependency checks."""

    def test_all_present(self, make_diagnostics, monkeypatch, caplog):
        """When all optional tools are installed, no prompts and all logged as found."""
        diag = make_diagnostics()
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        with caplog.at_level(logging.INFO):
            diag.run_optional()
        assert any("paplay" in r.message and "found" in r.message for r in caplog.records)
        assert any("ffmpeg" in r.message and "found" in r.message for r in caplog.records)
        assert any("xdotool" in r.message and "found" in r.message for r in caplog.records)

    def test_sound_declined_disables_config(self, make_diagnostics, monkeypatch, tmp_path, caplog):
        """Declining paplay install disables all sound_signal_* in config."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "notification": {
                "sound_signal_start": True,
                "sound_signal_processing": False,
                "sound_signal_done": True,
                "sound_signal_error": True,
            },
        }
        diag = make_diagnostics(config)
        present = {"ffmpeg", "xdotool"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with caplog.at_level(logging.INFO):
            diag._check_optional_sound()
        assert config["notification"]["sound_signal_start"] is False
        assert config["notification"]["sound_signal_done"] is False
        assert config["notification"]["sound_signal_error"] is False
        assert any("disabled" in r.message for r in caplog.records)

    def test_normalize_declined_disables_config(self, make_diagnostics, monkeypatch, tmp_path, caplog):
        """Declining ffmpeg install disables recording_normalize in config."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "audio": {"recording_normalize": True},
        }
        diag = make_diagnostics(config)
        present = {"paplay", "xdotool"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with caplog.at_level(logging.INFO):
            diag._check_optional_normalize()
        assert config["audio"]["recording_normalize"] is False
        assert any("disabled" in r.message for r in caplog.records)

    def test_paste_declined_disables_config(self, make_diagnostics, monkeypatch, tmp_path, caplog):
        """Declining xdotool install disables paste_auto in config."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "clipboard": {"paste_auto": True},
        }
        diag = make_diagnostics(config)
        present = {"paplay", "ffmpeg"}
        monkeypatch.setattr(
            "shutil.which",
            lambda x: f"/usr/bin/{x}" if x in present else None,
        )
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with caplog.at_level(logging.INFO):
            diag._check_optional_paste()
        assert config["clipboard"]["paste_auto"] is False
        assert any("disabled" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# AudioProcessor.normalize() ffmpeg fallback
# ---------------------------------------------------------------------------

class TestNormalizeFfmpegFallback:
    """AudioProcessor.normalize returns input_path when ffmpeg is missing."""

    def test_no_ffmpeg_returns_input(self, monkeypatch, tmp_path, caplog):
        from redictum import AudioProcessor

        monkeypatch.setattr("shutil.which", lambda x: None)
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"\x00" * 100)
        proc = AudioProcessor()
        with caplog.at_level(logging.WARNING):
            result = proc.normalize(audio)
        assert result == audio
        assert any("ffmpeg not found" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# WhisperInstaller._ensure_build_tools()
# ---------------------------------------------------------------------------

class TestRunOptionalForceReEnable:
    """force=True re-enables features when tool is found."""

    def test_force_reenables_sound(self, make_diagnostics, monkeypatch, caplog):
        """force=True + paplay found → re-enables sound_signal_* in config."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "notification": {
                "sound_signal_start": False,
                "sound_signal_processing": False,
                "sound_signal_done": False,
                "sound_signal_error": False,
            },
        }
        diag = make_diagnostics(config)
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        with caplog.at_level(logging.INFO):
            diag._check_optional_sound(force=True)
        assert config["notification"]["sound_signal_start"] is True
        assert config["notification"]["sound_signal_done"] is True
        assert config["notification"]["sound_signal_error"] is True

    def test_force_reenables_normalize(self, make_diagnostics, monkeypatch, caplog):
        """force=True + ffmpeg found → re-enables recording_normalize."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "audio": {"recording_normalize": False},
        }
        diag = make_diagnostics(config)
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        with caplog.at_level(logging.INFO):
            diag._check_optional_normalize(force=True)
        assert config["audio"]["recording_normalize"] is True

    def test_force_reenables_paste(self, make_diagnostics, monkeypatch, caplog):
        """force=True + xdotool found → re-enables paste_auto."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "clipboard": {"paste_auto": False},
        }
        diag = make_diagnostics(config)
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        with caplog.at_level(logging.INFO):
            diag._check_optional_paste(force=True)
        assert config["clipboard"]["paste_auto"] is True

    def test_force_decline_stays_disabled(self, make_diagnostics, monkeypatch, caplog):
        """force=True + tool missing + decline → feature stays disabled."""
        config = {
            "dependency": {"whisper_cli": "", "whisper_model": ""},
            "audio": {"recording_normalize": False},
        }
        diag = make_diagnostics(config)
        monkeypatch.setattr("shutil.which", lambda x: None)
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with caplog.at_level(logging.INFO):
            diag._check_optional_normalize(force=True)
        assert config["audio"]["recording_normalize"] is False


class TestSetupSubcommand:
    """./redictum setup: runs run_optional(force=True)."""

    def test_setup_calls_force(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        from redictum import RedictumApp, EXIT_OK

        app = RedictumApp(tmp_path)
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        # Write minimal config
        (tmp_path / "config.ini").write_text(
            "[dependency]\nwhisper_cli = x\nwhisper_model = x\n"
        )

        with patch("redictum.Diagnostics.run_optional") as mock_opt:
            result = app.run_setup()

        assert result == EXIT_OK
        mock_opt.assert_called_once_with(force=True)


class TestEnsureBuildTools:
    """WhisperInstaller._ensure_build_tools: checks cmake/build-essential."""

    def test_all_present_no_prompt(self, tmp_path, monkeypatch):
        from redictum import WhisperInstaller, ConfigManager

        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=0),
        )
        mgr = ConfigManager(tmp_path)
        installer = WhisperInstaller(mgr)
        installer._ensure_build_tools()  # should not raise

    def test_missing_declined_raises(self, tmp_path, monkeypatch):
        from redictum import WhisperInstaller, ConfigManager, RedictumError

        monkeypatch.setattr("shutil.which", lambda x: None)
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, **kw: MagicMock(returncode=1),
        )
        monkeypatch.setattr("builtins.input", lambda _: "n")
        mgr = ConfigManager(tmp_path)
        installer = WhisperInstaller(mgr)
        with pytest.raises(RedictumError, match="Build tools"):
            installer._ensure_build_tools()
