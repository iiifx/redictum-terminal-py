"""Tests for ConfigManager (INI-based)."""
from __future__ import annotations

from pathlib import Path

import pytest


class TestDeepCopy:
    """ConfigManager._deep_copy: recursive dict copy."""

    def test_nested_dict(self):
        from redictum import ConfigManager

        original = {"a": {"b": 1, "c": 2}, "d": 3}
        copy = ConfigManager._deep_copy(original)
        assert copy == original
        copy["a"]["b"] = 999
        assert original["a"]["b"] == 1

    def test_empty_dict(self):
        from redictum import ConfigManager

        assert ConfigManager._deep_copy({}) == {}


class TestDeepMerge:
    """ConfigManager._deep_merge: recursive in-place merge."""

    def test_overwrite_leaf(self):
        from redictum import ConfigManager

        base = {"a": 1, "b": 2}
        ConfigManager._deep_merge(base, {"a": 10})
        assert base == {"a": 10, "b": 2}

    def test_nested_merge(self):
        from redictum import ConfigManager

        base = {"x": {"y": 1, "z": 2}}
        ConfigManager._deep_merge(base, {"x": {"y": 99}})
        assert base == {"x": {"y": 99, "z": 2}}

    def test_new_keys(self):
        from redictum import ConfigManager

        base = {"a": 1}
        ConfigManager._deep_merge(base, {"b": 2, "c": {"d": 3}})
        assert base == {"a": 1, "b": 2, "c": {"d": 3}}


class TestFormatValue:
    """ConfigManager._format_value: Python → INI string."""

    def test_bool_true(self):
        from redictum import ConfigManager

        assert ConfigManager._format_value(True) == "true"

    def test_bool_false(self):
        from redictum import ConfigManager

        assert ConfigManager._format_value(False) == "false"

    def test_string(self):
        from redictum import ConfigManager

        assert ConfigManager._format_value("hello") == '"hello"'

    def test_int(self):
        from redictum import ConfigManager

        assert ConfigManager._format_value(42) == "42"


class TestStripQuotes:
    """ConfigManager._strip_quotes: surrounding quote removal."""

    def test_paired_quotes(self):
        from redictum import ConfigManager

        assert ConfigManager._strip_quotes('"hello"') == "hello"

    def test_empty_quotes(self):
        from redictum import ConfigManager

        assert ConfigManager._strip_quotes('""') == ""

    def test_space_in_quotes(self):
        from redictum import ConfigManager

        assert ConfigManager._strip_quotes('" "') == " "

    def test_no_quotes(self):
        from redictum import ConfigManager

        assert ConfigManager._strip_quotes("hello") == "hello"

    def test_single_quote_left(self):
        from redictum import ConfigManager

        assert ConfigManager._strip_quotes('"hello') == '"hello'

    def test_empty_string(self):
        from redictum import ConfigManager

        assert ConfigManager._strip_quotes("") == ""


class TestParseValue:
    """ConfigManager._parse_value: type-aware INI value parsing."""

    def test_bool_true(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("recording_normalize", '"true"') is True

    def test_bool_false(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("paste_auto", '"false"') is False

    def test_int(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("whisper_timeout", "120") == 120

    def test_float(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("hotkey_hold_delay", "0.6") == 0.6

    def test_string_with_quotes(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("whisper_language", '"auto"') == "auto"

    def test_string_without_quotes(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("whisper_language", "auto") == "auto"

    def test_invalid_int_raises(self):
        from redictum import ConfigManager, RedictumError

        with pytest.raises(RedictumError, match="expected integer"):
            ConfigManager._parse_value("whisper_timeout", "fast")

    def test_invalid_float_raises(self):
        from redictum import ConfigManager, RedictumError

        with pytest.raises(RedictumError, match="expected number"):
            ConfigManager._parse_value("hotkey_hold_delay", "abc")

    def test_paste_restore_delay_parsed(self):
        from redictum import ConfigManager

        assert ConfigManager._parse_value("paste_restore_delay", "0.5") == pytest.approx(0.5)

    def test_paste_restore_delay_invalid_raises(self):
        from redictum import ConfigManager, RedictumError

        with pytest.raises(RedictumError, match="expected number"):
            ConfigManager._parse_value("paste_restore_delay", "slow")


class TestExpandPaths:
    """ConfigManager._expand_paths: ~ expansion for whisper_cli/whisper_model."""

    def test_expands_tilde(self):
        from redictum import ConfigManager

        config = {
            "dependency": {
                "whisper_cli": "~/whisper.cpp/bin/cli",
                "whisper_model": "~/whisper.cpp/model.bin",
            },
        }
        result = ConfigManager._expand_paths(config)
        home = str(Path.home())
        assert result["dependency"]["whisper_cli"].startswith(home)
        assert result["dependency"]["whisper_model"].startswith(home)
        assert "~" not in result["dependency"]["whisper_cli"]


class TestLoad:
    """ConfigManager.load: file creation and INI parsing."""

    def test_missing_file_creates_default(self, config_dir):
        tmp_path, mgr = config_dir
        config = mgr.load()
        assert (tmp_path / "config.ini").exists()
        # Should have expanded paths (no ~)
        cli = config["dependency"]["whisper_cli"]
        assert "~" not in cli

    def test_valid_ini_merges(self, config_dir):
        tmp_path, mgr = config_dir
        ini_text = "[dependency]\nwhisper_timeout = 999\n"
        (tmp_path / "config.ini").write_text(ini_text, encoding="utf-8")
        config = mgr.load()
        assert config["dependency"]["whisper_timeout"] == 999
        # Default keys still present
        assert "whisper_language" in config["dependency"]

    def test_invalid_ini_raises(self, config_dir):
        from redictum import RedictumError

        tmp_path, mgr = config_dir
        (tmp_path / "config.ini").write_text("[broken\nno closing bracket", encoding="utf-8")
        with pytest.raises(RedictumError, match="Invalid INI"):
            mgr.load()

    def test_empty_file_returns_defaults(self, config_dir):
        tmp_path, mgr = config_dir
        (tmp_path / "config.ini").write_text("", encoding="utf-8")
        config = mgr.load()
        # Falls back to defaults
        assert "dependency" in config

    def test_invalid_int_in_ini_raises(self, config_dir):
        from redictum import RedictumError

        tmp_path, mgr = config_dir
        ini_text = "[dependency]\nwhisper_timeout = fast\n"
        (tmp_path / "config.ini").write_text(ini_text, encoding="utf-8")
        with pytest.raises(RedictumError, match="expected integer"):
            mgr.load()

    def test_invalid_float_in_ini_raises(self, config_dir):
        from redictum import RedictumError

        tmp_path, mgr = config_dir
        ini_text = "[input]\nhotkey_hold_delay = abc\n"
        (tmp_path / "config.ini").write_text(ini_text, encoding="utf-8")
        with pytest.raises(RedictumError, match="expected number"):
            mgr.load()

    def test_invalid_bool_in_ini_raises(self, config_dir):
        from redictum import RedictumError

        tmp_path, mgr = config_dir
        ini_text = "[audio]\nrecording_normalize = maybe\n"
        (tmp_path / "config.ini").write_text(ini_text, encoding="utf-8")
        with pytest.raises(RedictumError, match="expected boolean"):
            mgr.load()

    def test_quoted_string_values(self, config_dir):
        tmp_path, mgr = config_dir
        ini_text = '[clipboard]\npaste_prefix = ">>> "\npaste_postfix = ""\n'
        (tmp_path / "config.ini").write_text(ini_text, encoding="utf-8")
        config = mgr.load()
        assert config["clipboard"]["paste_prefix"] == ">>> "
        assert config["clipboard"]["paste_postfix"] == ""

    def test_yaml_migration(self, config_dir):
        """If config.yaml exists and config.ini doesn't, migrate."""
        pytest.importorskip("yaml")
        tmp_path, mgr = config_dir
        yaml_text = (
            "dependency:\n"
            "  whisper:\n"
            "    timeout: 999\n"
            "    language: ru\n"
        )
        (tmp_path / "config.yaml").write_text(yaml_text, encoding="utf-8")
        config = mgr.load()
        assert config["dependency"]["whisper_timeout"] == 999
        assert config["dependency"]["whisper_language"] == "ru"
        # yaml renamed to .bak
        assert not (tmp_path / "config.yaml").exists()
        assert (tmp_path / "config.yaml.bak").exists()


class TestUpdate:
    """ConfigManager.update: line-level value replacement."""

    def test_updates_value(self, config_dir):
        tmp_path, mgr = config_dir
        # Create default config first
        mgr.load()
        mgr.update({"whisper_timeout": 60})
        text = (tmp_path / "config.ini").read_text(encoding="utf-8")
        assert "whisper_timeout = 60" in text

    def test_preserves_comments(self, config_dir):
        tmp_path, mgr = config_dir
        mgr.load()
        mgr.update({"whisper_timeout": 60})
        text = (tmp_path / "config.ini").read_text(encoding="utf-8")
        # Comments should still be there
        assert "# Path to whisper-cli binary" in text

    def test_creates_file_from_template(self, config_dir):
        tmp_path, mgr = config_dir
        # No config.ini exists
        mgr.update({"whisper_timeout": 60})
        text = (tmp_path / "config.ini").read_text(encoding="utf-8")
        assert "whisper_timeout = 60" in text
