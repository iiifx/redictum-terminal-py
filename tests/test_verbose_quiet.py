"""Tests for --verbose / --quiet CLI flags and verbosity behaviour."""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# _rprint: level filtering
# ---------------------------------------------------------------------------

class TestRprint:
    """_rprint: output filtering based on _verbosity and level."""

    def _call_rprint(self, text, *, level=0, verbosity=0):
        """Call _rprint with a given _verbosity and return whether it printed."""
        import redictum
        old = redictum._verbosity
        try:
            redictum._verbosity = verbosity
            with patch.object(redictum, "_console", None):
                with patch("builtins.print") as mock_print:
                    redictum._rprint(text, level=level)
                    return mock_print.called
        finally:
            redictum._verbosity = old

    def test_normal_mode_default_level(self):
        assert self._call_rprint("hello", level=0, verbosity=0) is True

    def test_quiet_mode_suppresses_normal(self):
        assert self._call_rprint("hello", level=0, verbosity=-1) is False

    def test_quiet_mode_shows_critical(self):
        assert self._call_rprint("error!", level=-1, verbosity=-1) is True

    def test_verbose_mode_shows_verbose(self):
        assert self._call_rprint("debug info", level=1, verbosity=1) is True

    def test_normal_mode_hides_verbose(self):
        assert self._call_rprint("debug info", level=1, verbosity=0) is False


# ---------------------------------------------------------------------------
# _confirm: quiet auto-default
# ---------------------------------------------------------------------------

class TestConfirmQuiet:
    """_confirm: quiet mode returns default without input()."""

    def test_quiet_default_true(self):
        import redictum
        old = redictum._verbosity
        try:
            redictum._verbosity = -1
            result = redictum._confirm("Install?", default=True)
            assert result is True
        finally:
            redictum._verbosity = old

    def test_quiet_default_false(self):
        import redictum
        old = redictum._verbosity
        try:
            redictum._verbosity = -1
            result = redictum._confirm("Delete?", default=False)
            assert result is False
        finally:
            redictum._verbosity = old

    def test_normal_mode_calls_input(self):
        import redictum
        old = redictum._verbosity
        try:
            redictum._verbosity = 0
            with patch("builtins.input", return_value="y"):
                result = redictum._confirm("OK?", default=False)
                assert result is True
        finally:
            redictum._verbosity = old


# ---------------------------------------------------------------------------
# build_parser: -v / -q flags
# ---------------------------------------------------------------------------

class TestBuildParserFlags:
    """build_parser: --verbose and --quiet are mutually exclusive."""

    def test_verbose_flag(self):
        from redictum import build_parser
        parser = build_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose is True
        assert args.quiet is False

    def test_quiet_flag(self):
        from redictum import build_parser
        parser = build_parser()
        args = parser.parse_args(["-q"])
        assert args.quiet is True
        assert args.verbose is False

    def test_mutually_exclusive(self):
        from redictum import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-v", "-q"])


# ---------------------------------------------------------------------------
# run_language: quiet mode sets auto
# ---------------------------------------------------------------------------

class TestRunLanguageQuiet:
    """run_language: quiet mode sets auto without wizard."""

    @pytest.fixture()
    def app(self, tmp_path):
        import json

        from redictum import RedictumApp
        # Minimal init: config + state files
        (tmp_path / ".state").write_text(
            json.dumps({"initialized_at": "2024-01-01T00:00:00"})
        )
        (tmp_path / "config.ini").write_text(
            "[dependency]\n"
            "whisper_cli = /usr/bin/fake\n"
            "whisper_model = /tmp/fake.bin\n"
            "whisper_language = ru\n"
            "whisper_prompt = test prompt\n"
        )
        return RedictumApp(tmp_path)

    def test_quiet_sets_auto(self, app, tmp_path):
        import redictum
        old = redictum._verbosity
        try:
            redictum._verbosity = -1
            rc = app.run_language()
            assert rc == redictum.EXIT_OK
            config = app._config_mgr.load()
            assert config["dependency"]["whisper_language"] == "auto"
            assert config["dependency"]["whisper_prompt"] == "auto"
        finally:
            redictum._verbosity = old


# ---------------------------------------------------------------------------
# setup_logging: verbose enables DEBUG
# ---------------------------------------------------------------------------

class TestSetupLoggingVerbose:
    """setup_logging: verbose=True sets root logger to DEBUG."""

    def test_verbose_sets_debug(self, tmp_path):
        from redictum import setup_logging
        log_path = tmp_path / "logs" / "test.log"
        setup_logging(log_path, verbose=True, force=True)
        assert logging.getLogger().level == logging.DEBUG
        # Clean up: reset to INFO so other tests aren't affected
        setup_logging(log_path, verbose=False, force=True)

    def test_normal_sets_info(self, tmp_path):
        from redictum import setup_logging
        log_path = tmp_path / "logs" / "test.log"
        setup_logging(log_path, verbose=False, force=True)
        assert logging.getLogger().level == logging.INFO
