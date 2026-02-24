"""Tests for ConfigManager.sync(): detect missing keys and regenerate config."""
from __future__ import annotations

import pytest


@pytest.fixture()
def sync_env(tmp_path):
    """Create a ConfigManager with a written default config."""
    from redictum import ConfigManager
    mgr = ConfigManager(tmp_path)
    mgr._write_default()
    return tmp_path, mgr


# -- No-op cases -------------------------------------------------------------

class TestSyncNoop:
    """sync() should do nothing when config is absent or already complete."""

    def test_no_file(self, tmp_path):
        """sync() returns immediately when config file doesn't exist."""
        from redictum import ConfigManager
        mgr = ConfigManager(tmp_path)
        # No config file — nothing to sync
        mgr.sync()
        # No backup created
        assert not (tmp_path / "config.ini.bak").exists()

    def test_all_keys_present(self, sync_env):
        """sync() returns immediately when all keys are present."""
        tmp_path, mgr = sync_env
        original = mgr.path.read_text()
        mgr.sync()
        # File untouched — no backup, no rewrite
        assert not (tmp_path / "config.ini.bak").exists()
        assert mgr.path.read_text() == original


# -- Missing keys detection ---------------------------------------------------

class TestSyncMissingKeys:
    """sync() rewrites config when keys are missing, preserving user values."""

    def test_detects_missing_key(self, sync_env):
        """sync() detects a missing key and regenerates config."""
        tmp_path, mgr = sync_env
        # Remove a key from the config
        text = mgr.path.read_text()
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        mgr.sync()
        # Backup was created
        assert (tmp_path / "config.ini.bak").exists()
        # Key restored with default value
        new_text = mgr.path.read_text()
        assert "recording_volume_level = 30" in new_text

    def test_preserves_user_values(self, sync_env):
        """sync() keeps user-modified values when adding missing keys."""
        tmp_path, mgr = sync_env
        # Modify a value and remove another key
        text = mgr.path.read_text()
        text = text.replace("hotkey_hold_delay = 0.6", "hotkey_hold_delay = 1.0")
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        mgr.sync()
        # User's custom value preserved
        new_text = mgr.path.read_text()
        assert "hotkey_hold_delay = 1.0" in new_text
        # Missing key restored
        assert "recording_volume_level = 30" in new_text

    def test_preserves_boolean_values(self, sync_env):
        """sync() preserves boolean values (not mangled to Python True/False)."""
        tmp_path, mgr = sync_env
        # Set a boolean to false and remove a key
        text = mgr.path.read_text()
        text = text.replace("paste_auto = true", "paste_auto = false")
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        mgr.sync()
        new_text = mgr.path.read_text()
        assert "paste_auto = false" in new_text

    def test_preserves_string_values(self, sync_env):
        """sync() preserves quoted string values."""
        tmp_path, mgr = sync_env
        text = mgr.path.read_text()
        text = text.replace('paste_postfix = " "', 'paste_postfix = "\\n"')
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        mgr.sync()
        new_text = mgr.path.read_text()
        assert 'paste_postfix = "\\n"' in new_text


# -- Backup -------------------------------------------------------------------

class TestSyncBackup:
    """sync() creates .ini.bak before rewriting."""

    def test_creates_bak(self, sync_env):
        """sync() creates config.ini.bak from original."""
        tmp_path, mgr = sync_env
        text = mgr.path.read_text()
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        original = mgr.path.read_text()
        mgr.sync()
        bak = (tmp_path / "config.ini.bak").read_text()
        assert bak == original

    def test_backup_failure_aborts_sync(self, sync_env, monkeypatch):
        """sync() aborts when backup copy fails."""
        tmp_path, mgr = sync_env
        text = mgr.path.read_text()
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        original = mgr.path.read_text()

        monkeypatch.setattr("shutil.copy2", lambda *a, **kw: (_ for _ in ()).throw(OSError("no space")))
        mgr.sync()
        # Config file unchanged — sync was aborted
        assert mgr.path.read_text() == original


# -- Atomic write failures ---------------------------------------------------

class TestSyncAtomicWrite:
    """sync() cleans up on write failure."""

    def test_no_partial_tmp_files(self, sync_env, monkeypatch):
        """sync() removes .tmp file on write failure."""
        tmp_path, mgr = sync_env
        text = mgr.path.read_text()
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)

        def failing_write(fd, data):
            raise OSError("disk full")

        monkeypatch.setattr("os.write", failing_write)
        mgr.sync()
        # No leftover .tmp files
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []


# -- Broken config -----------------------------------------------------------

class TestSyncBrokenConfig:
    """sync() skips when config file is malformed INI."""

    def test_broken_ini_skips(self, tmp_path):
        """sync() returns silently when config is broken INI."""
        from redictum import ConfigManager
        mgr = ConfigManager(tmp_path)
        # Write invalid INI (no section header)
        mgr.path.write_text("this is not valid INI content\n[broken\n")
        mgr.sync()
        # No backup — sync didn't attempt rewrite
        assert not (tmp_path / "config.ini.bak").exists()


# -- Integration with load() -------------------------------------------------

class TestSyncLoadIntegration:
    """sync() + load(): synced config loads correctly."""

    def test_synced_config_loads(self, sync_env):
        """Config rewritten by sync() loads and returns all expected keys."""
        from redictum import DEFAULT_CONFIG
        tmp_path, mgr = sync_env
        # Remove a key to trigger sync
        text = mgr.path.read_text()
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        mgr.sync()
        config = mgr.load()
        # All default sections present
        for section in DEFAULT_CONFIG:
            assert section in config
        # Previously missing key has default value
        assert config["audio"]["recording_volume_level"] == 30

    def test_synced_config_preserves_overrides(self, sync_env):
        """User values survive sync() + load() round-trip."""
        tmp_path, mgr = sync_env
        text = mgr.path.read_text()
        text = text.replace("hotkey_hold_delay = 0.6", "hotkey_hold_delay = 1.5")
        text = text.replace("recording_volume_level = 30\n", "")
        mgr.path.write_text(text)
        mgr.sync()
        config = mgr.load()
        assert config["input"]["hotkey_hold_delay"] == 1.5
