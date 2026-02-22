"""Tests for language selector wizard and related functions."""
from __future__ import annotations

from unittest.mock import patch, MagicMock, call

import pytest


@pytest.fixture()
def app(tmp_path):
    from redictum import RedictumApp

    return RedictumApp(tmp_path)


# ---------------------------------------------------------------------------
# _language_wizard
# ---------------------------------------------------------------------------

class TestLanguageWizard:
    """_language_wizard: interactive language selection."""

    def test_select_by_number_returns_code_and_prompt(self):
        from redictum import _language_wizard, LANGUAGE_PROMPTS

        with patch("builtins.input", return_value="8"):
            result = _language_wizard("ru")

        assert result is not None
        code, prompt = result
        assert code == "ru"
        assert prompt == LANGUAGE_PROMPTS["ru"]

    def test_select_first_language(self):
        from redictum import _language_wizard, LANGUAGE_PROMPTS

        with patch("builtins.input", return_value="1"):
            result = _language_wizard("en")

        assert result == ("en", LANGUAGE_PROMPTS["en"])

    def test_select_last_language(self):
        from redictum import _language_wizard, LANGUAGE_NAMES, LANGUAGE_PROMPTS

        last_idx = len(LANGUAGE_NAMES)
        last_code = list(LANGUAGE_NAMES.keys())[-1]

        with patch("builtins.input", return_value=str(last_idx)):
            result = _language_wizard("en")

        assert result == (last_code, LANGUAGE_PROMPTS[last_code])

    def test_select_auto(self):
        from redictum import _language_wizard

        with patch("builtins.input", return_value="A"):
            result = _language_wizard("ru")

        assert result == ("auto", "auto")

    def test_select_auto_lowercase(self):
        from redictum import _language_wizard

        with patch("builtins.input", return_value="a"):
            result = _language_wizard("ru")

        assert result == ("auto", "auto")

    def test_select_other_known_code(self):
        from redictum import _language_wizard, LANGUAGE_PROMPTS

        with patch("builtins.input", side_effect=["0", "de"]):
            result = _language_wizard("en")

        assert result == ("de", LANGUAGE_PROMPTS["de"])

    def test_select_other_unknown_code(self):
        from redictum import _language_wizard

        with patch("builtins.input", side_effect=["0", "nl"]):
            result = _language_wizard("en")

        assert result == ("nl", "")

    def test_select_other_empty_code_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", side_effect=["0", ""]):
            result = _language_wizard("en")

        assert result is None

    def test_select_other_eof_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", side_effect=["0", EOFError]):
            result = _language_wizard("en")

        assert result is None

    def test_select_other_keyboard_interrupt_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", side_effect=["0", KeyboardInterrupt]):
            result = _language_wizard("en")

        assert result is None

    def test_invalid_number_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", return_value="99"):
            result = _language_wizard("en")

        assert result is None

    def test_zero_number_out_of_range_returns_none(self):
        """Negative number falls through to out-of-range check."""
        from redictum import _language_wizard

        with patch("builtins.input", return_value="-1"):
            result = _language_wizard("en")

        assert result is None

    def test_invalid_text_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", return_value="xyz"):
            result = _language_wizard("en")

        assert result is None

    def test_empty_input_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", return_value=""):
            result = _language_wizard("en")

        assert result is None

    def test_eof_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", side_effect=EOFError):
            result = _language_wizard("en")

        assert result is None

    def test_keyboard_interrupt_returns_none(self):
        from redictum import _language_wizard

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = _language_wizard("en")

        assert result is None


# ---------------------------------------------------------------------------
# _show_language_status
# ---------------------------------------------------------------------------

class TestShowLanguageStatus:
    """_show_language_status: display current language settings."""

    def test_auto_language(self, monkeypatch):
        from redictum import _show_language_status

        monkeypatch.setenv("LANG", "ru_RU.UTF-8")
        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        detected = _show_language_status(config)

        assert detected == "ru"

    def test_explicit_language(self, monkeypatch):
        from redictum import _show_language_status

        monkeypatch.setenv("LANG", "en_US.UTF-8")
        config = {"dependency": {"whisper_language": "de", "whisper_prompt": "some prompt"}}

        detected = _show_language_status(config)

        assert detected == "en"

    def test_empty_prompt(self, monkeypatch):
        from redictum import _show_language_status

        monkeypatch.setenv("LANG", "en_US.UTF-8")
        config = {"dependency": {"whisper_language": "en", "whisper_prompt": ""}}

        detected = _show_language_status(config)

        assert detected == "en"

    def test_long_prompt_truncated(self, monkeypatch, capsys):
        """Prompts longer than 60 chars are truncated with '...'."""
        from redictum import _show_language_status

        monkeypatch.setenv("LANG", "en_US.UTF-8")
        long_prompt = "A" * 80
        config = {"dependency": {"whisper_language": "en", "whisper_prompt": long_prompt}}

        _show_language_status(config)

        output = capsys.readouterr().out
        assert "..." in output
        assert long_prompt not in output

    def test_undetectable_locale(self, monkeypatch):
        """Empty LANG → detected is empty string, auto shows fallback message."""
        from redictum import _show_language_status

        monkeypatch.setenv("LANG", "")
        monkeypatch.delenv("LC_ALL", raising=False)
        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        detected = _show_language_status(config)

        assert detected == ""


# ---------------------------------------------------------------------------
# run_language
# ---------------------------------------------------------------------------

class TestRunLanguage:
    """RedictumApp.run_language: full command flow."""

    def test_cancel_at_first_confirm(self, app, tmp_path):
        """User says N to 'Change language?' → wizard not called, config unchanged."""
        from redictum import EXIT_OK, ConfigManager

        mgr = ConfigManager(tmp_path)
        mgr.load()
        original = mgr.load()

        with patch("redictum._confirm", return_value=False), \
             patch("redictum._show_language_status", return_value="ru"), \
             patch("redictum._language_wizard") as mock_wizard:
            result = app.run_language()

        assert result == EXIT_OK
        mock_wizard.assert_not_called()

        # Config unchanged
        config = mgr.load()
        assert config["dependency"]["whisper_language"] == original["dependency"]["whisper_language"]

    def test_wizard_returns_none(self, app, tmp_path):
        """Wizard cancelled → config unchanged."""
        from redictum import EXIT_OK, ConfigManager

        mgr = ConfigManager(tmp_path)
        mgr.load()
        original = mgr.load()

        confirms = iter([True])
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._show_language_status", return_value="ru"), \
             patch("redictum._language_wizard", return_value=None) as mock_wizard:
            result = app.run_language()

        assert result == EXIT_OK
        mock_wizard.assert_called_once()

        # Config unchanged
        config = mgr.load()
        assert config["dependency"]["whisper_language"] == original["dependency"]["whisper_language"]

    def test_cancel_at_save_confirm(self, app, tmp_path):
        """User picks language but says N to 'Save to config?' → config unchanged."""
        from redictum import EXIT_OK, ConfigManager, LANGUAGE_PROMPTS

        mgr = ConfigManager(tmp_path)
        mgr.load()
        original = mgr.load()

        confirms = iter([True, False])  # change=Y, save=N
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._show_language_status", return_value="ru"), \
             patch("redictum._language_wizard", return_value=("en", LANGUAGE_PROMPTS["en"])), \
             patch("redictum.Daemon") as mock_daemon_cls:
            mock_daemon_cls.return_value.status.return_value = None
            result = app.run_language()

        assert result == EXIT_OK

        # Config unchanged
        config = mgr.load()
        assert config["dependency"]["whisper_language"] == original["dependency"]["whisper_language"]

    def test_save_language(self, app, tmp_path):
        from redictum import EXIT_OK, ConfigManager, LANGUAGE_PROMPTS

        mgr = ConfigManager(tmp_path)
        mgr.load()

        confirms = iter([True, True])
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._show_language_status", return_value="ru"), \
             patch("redictum._language_wizard", return_value=("en", LANGUAGE_PROMPTS["en"])), \
             patch("redictum.Daemon") as mock_daemon_cls:
            mock_daemon_cls.return_value.status.return_value = None
            result = app.run_language()

        assert result == EXIT_OK

        config = mgr.load()
        assert config["dependency"]["whisper_language"] == "en"
        assert config["dependency"]["whisper_prompt"] == LANGUAGE_PROMPTS["en"]

    def test_save_auto(self, app, tmp_path):
        from redictum import EXIT_OK, ConfigManager

        mgr = ConfigManager(tmp_path)
        mgr.load()

        confirms = iter([True, True])
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._show_language_status", return_value="ru"), \
             patch("redictum._language_wizard", return_value=("auto", "auto")), \
             patch("redictum.Daemon") as mock_daemon_cls:
            mock_daemon_cls.return_value.status.return_value = None
            result = app.run_language()

        assert result == EXIT_OK

        config = mgr.load()
        assert config["dependency"]["whisper_language"] == "auto"
        assert config["dependency"]["whisper_prompt"] == "auto"

    def test_daemon_running_warning(self, app, tmp_path, capsys):
        """When daemon is running, warning is printed but save still proceeds."""
        from redictum import EXIT_OK, ConfigManager, LANGUAGE_PROMPTS

        mgr = ConfigManager(tmp_path)
        mgr.load()

        confirms = iter([True, True])
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._show_language_status", return_value="ru"), \
             patch("redictum._language_wizard", return_value=("en", LANGUAGE_PROMPTS["en"])), \
             patch("redictum.Daemon") as mock_daemon_cls:
            mock_daemon_cls.return_value.status.return_value = 12345
            result = app.run_language()

        assert result == EXIT_OK

        output = capsys.readouterr().out
        assert "Daemon is running" in output or "Restart" in output

        config = mgr.load()
        assert config["dependency"]["whisper_language"] == "en"


# ---------------------------------------------------------------------------
# _first_run_language_check
# ---------------------------------------------------------------------------

class TestFirstRunLanguageCheck:
    """RedictumApp._first_run_language_check: first-run prompt."""

    def test_default_no_skips(self, app, monkeypatch):
        """Default N → wizard not called, config unchanged."""
        monkeypatch.setenv("LANG", "ru_RU.UTF-8")
        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        with patch("redictum._confirm", return_value=False), \
             patch("redictum._language_wizard") as mock_wizard:
            app._first_run_language_check(config)

        mock_wizard.assert_not_called()
        assert config["dependency"]["whisper_language"] == "auto"

    def test_yes_then_select_language(self, app, tmp_path, monkeypatch):
        """User says Y, picks a language, confirms save → config updated."""
        from redictum import ConfigManager, LANGUAGE_PROMPTS

        monkeypatch.setenv("LANG", "ru_RU.UTF-8")
        mgr = ConfigManager(tmp_path)
        mgr.load()

        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        confirms = iter([True, True])
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._language_wizard", return_value=("en", LANGUAGE_PROMPTS["en"])):
            app._first_run_language_check(config)

        saved = mgr.load()
        assert saved["dependency"]["whisper_language"] == "en"

    def test_yes_then_wizard_cancel(self, app, monkeypatch):
        """User says Y but cancels wizard → no changes."""
        monkeypatch.setenv("LANG", "en_US.UTF-8")
        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        confirms = iter([True])
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._language_wizard", return_value=None):
            app._first_run_language_check(config)

        assert config["dependency"]["whisper_language"] == "auto"

    def test_yes_then_decline_save(self, app, tmp_path, monkeypatch):
        """User says Y, picks language, but declines save → config unchanged."""
        from redictum import ConfigManager, LANGUAGE_PROMPTS

        monkeypatch.setenv("LANG", "ru_RU.UTF-8")
        mgr = ConfigManager(tmp_path)
        mgr.load()
        original = mgr.load()

        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        confirms = iter([True, False])  # change=Y, save=N
        with patch("redictum._confirm", side_effect=confirms), \
             patch("redictum._language_wizard", return_value=("en", LANGUAGE_PROMPTS["en"])):
            app._first_run_language_check(config)

        saved = mgr.load()
        assert saved["dependency"]["whisper_language"] == original["dependency"]["whisper_language"]

    def test_undetectable_locale(self, app, monkeypatch):
        """Empty LANG → fallback message, wizard still offered."""
        monkeypatch.setenv("LANG", "")
        monkeypatch.delenv("LC_ALL", raising=False)
        config = {"dependency": {"whisper_language": "auto", "whisper_prompt": "auto"}}

        with patch("redictum._confirm", return_value=False), \
             patch("redictum._language_wizard") as mock_wizard:
            app._first_run_language_check(config)

        # Should not crash, wizard not called because user said N
        mock_wizard.assert_not_called()


# ---------------------------------------------------------------------------
# build_parser & main dispatch
# ---------------------------------------------------------------------------

class TestBuildParserLanguage:
    """build_parser includes language subcommand."""

    def test_language_subcommand_exists(self):
        from redictum import build_parser

        parser = build_parser()
        args = parser.parse_args(["language"])
        assert args.command == "language"


# ---------------------------------------------------------------------------
# LANGUAGE_NAMES consistency
# ---------------------------------------------------------------------------

class TestLanguageNames:
    """LANGUAGE_NAMES matches LANGUAGE_PROMPTS keys."""

    def test_keys_match(self):
        from redictum import LANGUAGE_NAMES, LANGUAGE_PROMPTS

        assert set(LANGUAGE_NAMES.keys()) == set(LANGUAGE_PROMPTS.keys())

    def test_order_matches(self):
        """Keys are in the same order in both dicts."""
        from redictum import LANGUAGE_NAMES, LANGUAGE_PROMPTS

        assert list(LANGUAGE_NAMES.keys()) == list(LANGUAGE_PROMPTS.keys())
