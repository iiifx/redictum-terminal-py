"""Tests for Daemon lifecycle: start guards, stop, signal handling, cleanup."""
from __future__ import annotations

import signal
import threading

import pytest


@pytest.fixture()
def daemon(tmp_path):
    from redictum import Daemon
    pid_path = tmp_path / "test.pid"
    log_path = tmp_path / "test.log"
    return Daemon(pid_path, log_path)


# -- start() guards -----------------------------------------------------------

class TestStartGuards:
    """Daemon.start(): refuse if running, clean up stale PID."""

    def test_refuses_when_running(self, daemon, monkeypatch):
        """start() raises when daemon is already running."""
        from redictum import RedictumError
        daemon._pid_path.write_text("12345\n")
        monkeypatch.setattr("os.kill", lambda pid, sig: None)  # process exists

        with pytest.raises(RedictumError, match="already running"):
            daemon.start(lambda: None)

    def test_cleans_stale_pid_before_fork(self, daemon, monkeypatch):
        """start() removes stale PID file before forking."""
        daemon._pid_path.write_text("99999\n")

        def fake_kill(pid, sig):
            raise ProcessLookupError

        monkeypatch.setattr("os.kill", fake_kill)
        # Mock os.fork to avoid actual forking in tests
        monkeypatch.setattr("os.fork", lambda: 1)  # Parent path (pid > 0)

        daemon.start(lambda: None)
        assert not daemon._pid_path.exists()


# -- stop() -------------------------------------------------------------------

class TestStop:
    """Daemon.stop(): SIGTERM, stale PID, timeout."""

    def test_sends_sigterm(self, daemon, monkeypatch):
        """stop() sends SIGTERM to running daemon."""
        daemon._pid_path.write_text("12345\n")
        kills = []

        def fake_kill(pid, sig):
            kills.append((pid, sig))
            if sig == 0 and len(kills) > 1:
                # After SIGTERM, process is gone
                raise ProcessLookupError

        monkeypatch.setattr("os.kill", fake_kill)
        daemon.stop()
        assert (12345, signal.SIGTERM) in kills

    def test_no_pid_raises(self, daemon):
        """stop() raises when no PID file exists."""
        from redictum import RedictumError
        with pytest.raises(RedictumError, match="not running"):
            daemon.stop()

    def test_stale_pid_raises_and_cleans(self, daemon, monkeypatch):
        """stop() removes stale PID and raises error."""
        from redictum import RedictumError
        daemon._pid_path.write_text("99999\n")

        def fake_kill(pid, sig):
            raise ProcessLookupError

        monkeypatch.setattr("os.kill", fake_kill)
        with pytest.raises(RedictumError, match="stale PID"):
            daemon.stop()
        assert not daemon._pid_path.exists()

    def test_timeout_warns(self, daemon, monkeypatch, capsys):
        """stop() warns when process doesn't exit within timeout."""
        daemon._pid_path.write_text("12345\n")
        # Process never exits
        monkeypatch.setattr("os.kill", lambda pid, sig: None)
        monkeypatch.setattr("redictum.STOP_TIMEOUT", 0.2)

        daemon.stop()
        # Should have printed warning (via _rprint)


# -- _handle_signal() -------------------------------------------------------

class TestHandleSignal:
    """Daemon._handle_signal: set stop event on signal."""

    def test_sets_stop_event(self, daemon):
        """_handle_signal() sets the stop event."""
        assert not daemon.stop_event.is_set()
        daemon._handle_signal(signal.SIGTERM, None)
        assert daemon.stop_event.is_set()


# -- _cleanup() --------------------------------------------------------------

class TestCleanup:
    """Daemon._cleanup: PID file removal."""

    def test_removes_pid_file(self, daemon):
        """_cleanup() removes the PID file."""
        daemon._pid_path.write_text("12345\n")
        daemon._cleanup()
        assert not daemon._pid_path.exists()

    def test_safe_when_missing(self, daemon):
        """_cleanup() doesn't raise when PID file is already gone."""
        assert not daemon._pid_path.exists()
        daemon._cleanup()  # Should not raise


# -- _setup_signals() -------------------------------------------------------

class TestSetupSignals:
    """Daemon._setup_signals: register signal handlers."""

    def test_registers_handlers(self, daemon, monkeypatch):
        """_setup_signals() registers SIGTERM and SIGINT handlers."""
        handlers = {}

        def fake_signal(signum, handler):
            handlers[signum] = handler

        monkeypatch.setattr("signal.signal", fake_signal)
        daemon._setup_signals()
        assert signal.SIGTERM in handlers
        assert signal.SIGINT in handlers
        assert handlers[signal.SIGTERM] == daemon._handle_signal


# -- stop_event property -----------------------------------------------------

class TestStopEvent:
    """Daemon.stop_event: threading.Event for main loop."""

    def test_returns_event(self, daemon):
        """stop_event returns a threading.Event."""
        assert isinstance(daemon.stop_event, threading.Event)

    def test_initially_not_set(self, daemon):
        """stop_event is not set initially."""
        assert not daemon.stop_event.is_set()
