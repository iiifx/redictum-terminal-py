"""Tests for ConfigManager."""
from __future__ import annotations

from pathlib import Path

import pytest


class TestDeepCopy:
    """ConfigManager._deep_copy: recursive dict copy."""

    def test_nested_dict(self):
        from redictum import ConfigManager

        original = {"a": {"b": {"c": 1}}, "d": 2}
        copy = ConfigManager._deep_copy(original)
        assert copy == original
        copy["a"]["b"]["c"] = 999
        assert original["a"]["b"]["c"] == 1

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
    """ConfigManager._format_value: Python → YAML string."""

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


class TestExpandPaths:
    """ConfigManager._expand_paths: ~ expansion for cli/model."""

    def test_expands_tilde(self):
        from redictum import ConfigManager

        config = {
            "dependency": {
                "whisper": {
                    "cli": "~/whisper.cpp/bin/cli",
                    "model": "~/whisper.cpp/model.bin",
                },
            },
        }
        result = ConfigManager._expand_paths(config)
        home = str(Path.home())
        assert result["dependency"]["whisper"]["cli"].startswith(home)
        assert result["dependency"]["whisper"]["model"].startswith(home)
        assert "~" not in result["dependency"]["whisper"]["cli"]


class TestLoad:
    """ConfigManager.load: file creation and YAML parsing."""

    def test_missing_file_creates_default(self, config_dir):
        tmp_path, mgr = config_dir
        config = mgr.load()
        assert (tmp_path / "config.yaml").exists()
        # Should have expanded paths (no ~)
        cli = config["dependency"]["whisper"]["cli"]
        assert "~" not in cli

    def test_valid_yaml_merges(self, config_dir):
        tmp_path, mgr = config_dir
        yaml_text = "dependency:\n  whisper:\n    timeout: 999\n"
        (tmp_path / "config.yaml").write_text(yaml_text, encoding="utf-8")
        config = mgr.load()
        assert config["dependency"]["whisper"]["timeout"] == 999
        # Default keys still present
        assert "language" in config["dependency"]["whisper"]

    def test_invalid_yaml_raises(self, config_dir):
        from redictum import RedictumError

        tmp_path, mgr = config_dir
        (tmp_path / "config.yaml").write_text(":\n  :\n    bad: [", encoding="utf-8")
        with pytest.raises(RedictumError, match="Invalid YAML"):
            mgr.load()

    def test_non_dict_yaml_treated_as_empty(self, config_dir):
        tmp_path, mgr = config_dir
        (tmp_path / "config.yaml").write_text('"just a string"', encoding="utf-8")
        config = mgr.load()
        # Falls back to defaults
        assert "dependency" in config


class TestUpdate:
    """ConfigManager.update: line-level value replacement."""

    def test_updates_value(self, config_dir):
        tmp_path, mgr = config_dir
        # Create default config first
        mgr.load()
        mgr.update({"timeout": 60})
        text = (tmp_path / "config.yaml").read_text(encoding="utf-8")
        assert "timeout: 60" in text

    def test_preserves_comments(self, config_dir):
        tmp_path, mgr = config_dir
        mgr.load()
        mgr.update({"timeout": "60"})
        text = (tmp_path / "config.yaml").read_text(encoding="utf-8")
        # Comments should still be there
        assert "# Path to whisper-cli binary" in text

    def test_creates_file_from_template(self, config_dir):
        tmp_path, mgr = config_dir
        # No config.yaml exists
        mgr.update({"timeout": 60})
        text = (tmp_path / "config.yaml").read_text(encoding="utf-8")
        assert "timeout: 60" in text
