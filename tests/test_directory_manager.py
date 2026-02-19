"""Tests for DirectoryManager."""
from __future__ import annotations


class TestEnsure:
    """DirectoryManager.ensure: create required directories."""

    def test_creates_dirs(self, tmp_path):
        from redictum import DirectoryManager

        mgr = DirectoryManager(tmp_path)
        mgr.ensure()
        for name in ("audio", "transcripts", "logs"):
            assert (tmp_path / name).is_dir()

    def test_idempotent(self, tmp_path):
        from redictum import DirectoryManager

        mgr = DirectoryManager(tmp_path)
        mgr.ensure()
        mgr.ensure()  # no error
        for name in ("audio", "transcripts", "logs"):
            assert (tmp_path / name).is_dir()
