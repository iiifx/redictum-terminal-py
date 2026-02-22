"""Tests for Daemon: PID file handling, is_running, status."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def daemon(tmp_path):
    from redictum import Daemon

    pid_path = tmp_path / "test.pid"
    log_path = tmp_path / "test.log"
    return Daemon(pid_path, log_path)


class TestReadPid:
    """Daemon._read_pid: read PID from file."""

    def test_valid_pid(self, daemon):
        daemon._pid_path.write_text("12345\n")
        assert daemon._read_pid() == 12345

    def test_no_file(self, daemon):
        assert daemon._read_pid() is None

    def test_garbage(self, daemon):
        daemon._pid_path.write_text("not-a-number\n")
        assert daemon._read_pid() is None


class TestIsRunning:
    """Daemon._is_running: signal-based process check."""

    def test_process_exists(self, daemon, monkeypatch):
        monkeypatch.setattr("os.kill", lambda pid, sig: None)
        assert daemon._is_running(12345) is True

    def test_process_not_found(self, daemon, monkeypatch):
        def fake_kill(pid, sig):
            raise ProcessLookupError

        monkeypatch.setattr("os.kill", fake_kill)
        assert daemon._is_running(12345) is False

    def test_permission_error(self, daemon, monkeypatch):
        def fake_kill(pid, sig):
            raise PermissionError

        monkeypatch.setattr("os.kill", fake_kill)
        assert daemon._is_running(12345) is True


class TestStatus:
    """Daemon.status: running/stale/not running."""

    def test_running(self, daemon, monkeypatch):
        daemon._pid_path.write_text("12345\n")
        monkeypatch.setattr("os.kill", lambda pid, sig: None)
        assert daemon.status() == 12345

    def test_stale_pid(self, daemon, monkeypatch):
        daemon._pid_path.write_text("99999\n")

        def fake_kill(pid, sig):
            raise ProcessLookupError

        monkeypatch.setattr("os.kill", fake_kill)
        result = daemon.status()
        assert result is None
        # Stale PID file should be cleaned up
        assert not daemon._pid_path.exists()

    def test_no_pid_file(self, daemon):
        assert daemon.status() is None


class TestWritePid:
    """Daemon._write_pid: atomic creation with explicit permissions."""

    def test_creates_file_with_pid(self, daemon):
        daemon._write_pid()
        content = daemon._pid_path.read_text()
        assert content.strip() == str(os.getpid())

    def test_not_world_writable(self, daemon):
        daemon._write_pid()
        mode = daemon._pid_path.stat().st_mode
        assert not bool(mode & stat.S_IWOTH)

    def test_overwrites_stale_file(self, daemon):
        daemon._pid_path.write_text("99999\n")
        daemon._write_pid()
        content = daemon._pid_path.read_text()
        assert content.strip() == str(os.getpid())
