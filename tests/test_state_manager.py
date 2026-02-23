"""Tests for StateManager: persistent JSON state file."""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def mgr(tmp_path):
    from redictum import StateManager

    return StateManager(tmp_path)


class TestPath:
    """StateManager.path property."""

    def test_returns_correct_path(self, tmp_path):
        from redictum import StateManager, STATE_FILENAME

        mgr = StateManager(tmp_path)
        assert mgr.path == tmp_path / STATE_FILENAME


class TestLoad:
    """StateManager.load: read state from disk."""

    def test_missing_file_returns_empty(self, mgr):
        assert mgr.load() == {}

    def test_valid_json_roundtrip(self, mgr):
        mgr.path.write_text('{"key": "value"}', encoding="utf-8")
        assert mgr.load() == {"key": "value"}

    def test_corrupt_json_returns_empty(self, mgr):
        mgr.path.write_text("{broken json!!!", encoding="utf-8")
        assert mgr.load() == {}

    def test_non_dict_json_returns_empty(self, mgr):
        for value in ["null", "[]", "42", '"string"']:
            mgr.path.write_text(value, encoding="utf-8")
            assert mgr.load() == {}, f"Expected {{}} for JSON: {value}"


class TestSave:
    """StateManager.save: write state to disk."""

    def test_roundtrip(self, mgr):
        data = {"initialized_at": "2024-01-15T12:34:56", "version": "1.0.0"}
        mgr.save(data)
        assert mgr.load() == data

    def test_creates_file(self, mgr):
        assert not mgr.path.exists()
        mgr.save({"x": 1})
        assert mgr.path.exists()

    def test_uses_indent(self, mgr):
        mgr.save({"a": 1})
        content = mgr.path.read_text(encoding="utf-8")
        assert "  " in content  # indent=2

    def test_overwrites_existing(self, mgr):
        mgr.save({"old": "data"})
        mgr.save({"new": "data"})
        state = mgr.load()
        assert state == {"new": "data"}
        assert "old" not in state

    def test_unicode_roundtrip(self, mgr):
        data = {"note": "привет мир", "emoji": "日本語"}
        mgr.save(data)
        assert mgr.load() == data

    def test_no_temp_files_left_after_save(self, mgr, tmp_path):
        mgr.save({"a": 1})
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_old_state_preserved_on_write_error(self, mgr, monkeypatch):
        """If os.write fails, the original file must remain intact."""
        mgr.save({"original": True})

        def failing_write(fd, data):
            raise OSError("disk full")

        monkeypatch.setattr("os.write", failing_write)
        with pytest.raises(OSError, match="disk full"):
            mgr.save({"corrupted": True})

        # Original data must survive
        assert mgr.load() == {"original": True}

    def test_no_temp_files_left_on_error(self, mgr, tmp_path, monkeypatch):
        """Temp file must be cleaned up on write failure."""
        def failing_write(fd, data):
            raise OSError("disk full")

        monkeypatch.setattr("os.write", failing_write)
        with pytest.raises(OSError):
            mgr.save({"x": 1})

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []


class TestGetSet:
    """StateManager.get / set convenience methods."""

    def test_missing_key_returns_default(self, mgr):
        assert mgr.get("nonexistent") is None
        assert mgr.get("nonexistent", 42) == 42

    def test_existing_key(self, mgr):
        mgr.save({"foo": "bar"})
        assert mgr.get("foo") == "bar"

    def test_set_creates_and_persists(self, mgr):
        mgr.set("key", "value")
        assert mgr.get("key") == "value"
        # Re-read from disk
        raw = json.loads(mgr.path.read_text(encoding="utf-8"))
        assert raw["key"] == "value"

    def test_set_preserves_other_keys(self, mgr):
        mgr.save({"existing": True})
        mgr.set("new_key", 123)
        state = mgr.load()
        assert state["existing"] is True
        assert state["new_key"] == 123


