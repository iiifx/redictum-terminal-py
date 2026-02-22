"""Tests for module-level helper functions."""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest


class TestDetectLanguage:
    """_detect_language: derive 2-letter code from system locale."""

    @pytest.mark.parametrize(
        "lang_env, expected",
        [
            ("ru_RU.UTF-8", "ru"),
            ("en_US.UTF-8", "en"),
            ("uk_UA", "uk"),
            ("de_DE.utf8", "de"),
            ("fr_FR", "fr"),
            ("C", ""),
            ("", ""),
        ],
    )
    def test_detect_language(self, lang_env, expected, monkeypatch):
        from redictum import _detect_language

        # locale.getdefaultlocale() is deprecated; patch it + LANG env var
        monkeypatch.setattr("locale.getdefaultlocale", lambda: (lang_env, "UTF-8"))
        monkeypatch.setenv("LANG", lang_env)
        result = _detect_language()
        assert result == expected


class TestLogTranscript:
    """_log_transcript: append timestamped text to a daily file."""

    def test_creates_file_and_appends(self, tmp_path):
        from redictum import _log_transcript

        _log_transcript(tmp_path, "hello world")
        files = list(tmp_path.glob("*.txt"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert re.match(r"\[\d{2}:\d{2}:\d{2}\] hello world\n", content)

    def test_appends_multiple(self, tmp_path):
        from redictum import _log_transcript

        _log_transcript(tmp_path, "first")
        _log_transcript(tmp_path, "second")
        files = list(tmp_path.glob("*.txt"))
        assert len(files) == 1
        lines = files[0].read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert "first" in lines[0]
        assert "second" in lines[1]


class TestGenerateTones:
    """_generate_tones: returns 4 named tone sample lists."""

    def test_returns_four_tones(self):
        from redictum import _generate_tones

        tones = _generate_tones()
        assert set(tones.keys()) == {"start", "processing", "done", "error"}

    def test_tones_are_nonempty_float_lists(self):
        from redictum import _generate_tones

        for name, samples in _generate_tones().items():
            assert len(samples) > 0, f"{name} is empty"
            assert all(isinstance(s, float) for s in samples), f"{name} has non-float"


class TestRprint:
    """_rprint: strip rich markup when console unavailable."""

    def test_plain_fallback(self, monkeypatch, capsys):
        import redictum

        monkeypatch.setattr(redictum, "_console", None)
        redictum._rprint("[bold]hello[/bold]")
        out = capsys.readouterr().out
        assert "hello" in out
        assert "[bold]" not in out

    def test_rich_console_used(self, monkeypatch):
        import redictum

        mock_console = MagicMock()
        monkeypatch.setattr(redictum, "_console", mock_console)
        redictum._rprint("[green]ok[/green]")
        mock_console.print.assert_called_once_with("[green]ok[/green]")


class TestBuildParser:
    """build_parser: subcommands and flags."""

    def test_subcommands_present(self):
        from redictum import build_parser

        parser = build_parser()
        # Check that known subcommands parse without error
        for cmd in ("start", "stop", "status", "whisper", "language"):
            args = parser.parse_args([cmd])
            assert args.command == cmd

    def test_no_command_default(self):
        from redictum import build_parser

        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_config_flag(self):
        from redictum import build_parser

        parser = build_parser()
        args = parser.parse_args(["--config"])
        assert args.config is True

    def test_version_flag(self):
        from redictum import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0
