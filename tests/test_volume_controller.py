"""Tests for VolumeController: reduce/restore volume via pactl."""
from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def tmp_lock(tmp_path, monkeypatch):
    """Redirect VolumeController lock file to a temp directory."""
    lock_path = tmp_path / "redictum-volume.json"
    monkeypatch.setattr(
        "redictum.VolumeController._resolve_lock_path",
        classmethod(lambda cls: lock_path),
    )
    return lock_path


@pytest.fixture()
def vc(tmp_lock):
    from redictum import VolumeController
    return VolumeController(volume_level=30)


def _fake_pactl(volume_pct: int = 50):
    """Return a fake subprocess.run that simulates pactl get/set."""
    calls: list[list[str]] = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        result = MagicMock()
        result.stdout = f"Volume: front-left: 32768 /  {volume_pct}% / -18.06 dB"
        result.returncode = 0
        return result

    return fake_run, calls


# -- reduce() ---------------------------------------------------------------

class TestReduce:
    """VolumeController.reduce(): save current volume and lower it."""

    def test_normal_path(self, vc, tmp_lock, monkeypatch):
        """reduce() reads current volume and sets target = current * level / 100."""
        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()

        assert len(calls) == 2
        assert calls[0][1] == "get-sink-volume"
        # target = 50 * 30 / 100 = 15
        assert calls[1] == ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "15%"]
        assert vc._active is True
        # Lock file has original volume and our PID
        data = json.loads(tmp_lock.read_text())
        assert data["volume"] == 50
        assert os.getpid() in data["pids"]

    def test_guard_repeated_call(self, vc, monkeypatch):
        """reduce() is a no-op when already reduced (_active is True)."""
        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        count_after_first = len(calls)
        vc.reduce()
        assert len(calls) == count_after_first

    def test_pactl_not_found(self, vc, monkeypatch):
        """reduce() silently skips when pactl is not installed."""
        def fake_run(cmd, **kw):
            raise FileNotFoundError("pactl")

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._active is False

    def test_timeout(self, vc, monkeypatch):
        """reduce() silently skips on timeout."""
        def fake_run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 2)

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._active is False

    def test_unparsable_output(self, vc, monkeypatch):
        """reduce() skips when pactl output doesn't contain volume percentage."""
        def fake_run(cmd, **kw):
            result = MagicMock()
            result.stdout = "no volume info here"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._active is False

    def test_set_volume_failure(self, vc, tmp_lock, monkeypatch):
        """reduce() registers in lock file even if set-sink-volume fails."""
        call_count = [0]

        def fake_run(cmd, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                result = MagicMock()
                result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
                return result
            raise FileNotFoundError("pactl")

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._active is True
        data = json.loads(tmp_lock.read_text())
        assert data["volume"] == 50

    def test_relative_calculation(self, tmp_lock, monkeypatch):
        """Target volume is relative to original: level=30, current=80% -> 24%."""
        from redictum import VolumeController
        vc = VolumeController(volume_level=30)
        fake_run, calls = _fake_pactl(80)
        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert calls[1][-1] == "24%"

    def test_volume_level_clamped(self):
        """volume_level is clamped to [0, 100]."""
        from redictum import VolumeController
        vc_low = VolumeController(volume_level=-10)
        assert vc_low._volume_level == 0
        vc_high = VolumeController(volume_level=150)
        assert vc_high._volume_level == 100


# -- restore() --------------------------------------------------------------

class TestRestore:
    """VolumeController.restore(): put volume back to saved value."""

    def test_normal_path(self, vc, tmp_lock, monkeypatch):
        """restore() calls set-sink-volume with the original percentage."""
        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        calls.clear()
        vc.restore()
        assert calls == [["pactl", "set-sink-volume", "@DEFAULT_SINK@", "50%"]]
        assert vc._active is False
        assert not tmp_lock.exists()

    def test_guard_no_saved(self, vc, monkeypatch):
        """restore() is a no-op when there is no saved volume."""
        calls: list = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: calls.append(a))
        vc.restore()
        assert calls == []

    def test_idempotent(self, vc, monkeypatch):
        """restore() can be called multiple times safely."""
        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        calls.clear()
        vc.restore()
        vc.restore()
        vc.restore()
        # Only one restore call
        assert len(calls) == 1

    def test_pactl_error_on_restore(self, vc, monkeypatch):
        """restore() silently handles pactl errors."""
        call_count = [0]

        def fake_run(cmd, **kw):
            call_count[0] += 1
            if call_count[0] <= 2:
                result = MagicMock()
                result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
                return result
            raise subprocess.TimeoutExpired(cmd, 2)

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        vc.restore()  # Should not raise
        assert vc._active is False


# -- Multi-instance ----------------------------------------------------------

class TestMultiInstance:
    """Shared lock file handles multiple instances correctly."""

    def test_second_instance_preserves_original(self, tmp_lock, monkeypatch):
        """Second instance does not overwrite the original volume."""
        from redictum import VolumeController
        vc1 = VolumeController(volume_level=30)
        vc1._pid = 1001
        vc2 = VolumeController(volume_level=30)
        vc2._pid = 1002

        call_count = [0]

        def fake_run(cmd, **kw):
            call_count[0] += 1
            result = MagicMock()
            # First get returns 50% (original), later gets return 15% (reduced)
            if cmd[1] == "get-sink-volume":
                vol = 50 if call_count[0] <= 2 else 15
                result.stdout = f"Volume: front-left: 32768 /  {vol}% / dB"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        # Both PIDs are "alive" in our test
        monkeypatch.setattr(
            "redictum.VolumeController._pid_alive",
            staticmethod(lambda p: p in (1001, 1002)),
        )

        vc1.reduce()
        data = json.loads(tmp_lock.read_text())
        assert data["volume"] == 50

        vc2.reduce()
        data = json.loads(tmp_lock.read_text())
        assert data["volume"] == 50  # original preserved
        assert len(data["pids"]) == 2

    def test_first_restore_defers(self, tmp_lock, monkeypatch):
        """First instance to restore does NOT change volume (others still active)."""
        from redictum import VolumeController
        vc1 = VolumeController(volume_level=30)
        vc1._pid = 1001
        vc2 = VolumeController(volume_level=30)
        vc2._pid = 1002

        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr(
            "redictum.VolumeController._pid_alive",
            staticmethod(lambda p: p in (1001, 1002)),
        )

        vc1.reduce()
        vc2.reduce()
        calls.clear()

        vc1.restore()
        # No set-sink-volume call — deferred
        assert all(c[1] != "set-sink-volume" for c in calls)
        assert tmp_lock.exists()

    def test_last_restore_restores_original(self, tmp_lock, monkeypatch):
        """Last instance to restore puts volume back to original."""
        from redictum import VolumeController
        vc1 = VolumeController(volume_level=30)
        vc1._pid = 1001
        vc2 = VolumeController(volume_level=30)
        vc2._pid = 1002

        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr(
            "redictum.VolumeController._pid_alive",
            staticmethod(lambda p: p in (1001, 1002)),
        )

        vc1.reduce()
        vc2.reduce()
        vc1.restore()
        calls.clear()

        vc2.restore()
        assert ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "50%"] in calls
        assert not tmp_lock.exists()

    def test_dead_pid_cleanup(self, tmp_lock, monkeypatch):
        """Dead PIDs from crashed instances are cleaned on acquire."""
        from redictum import VolumeController
        vc = VolumeController(volume_level=30)

        # Seed lock file with a dead PID
        dead_pid = 99999
        tmp_lock.write_text(json.dumps({"volume": 80, "pids": [dead_pid]}))

        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr(
            "redictum.VolumeController._pid_alive",
            staticmethod(lambda p: p != dead_pid),
        )

        vc.reduce()
        data = json.loads(tmp_lock.read_text())
        # Dead PID cleaned, original volume reset to current (50)
        assert dead_pid not in data["pids"]
        assert data["volume"] == 50

    def test_corrupted_lock_file(self, tmp_lock, monkeypatch):
        """Corrupted lock file is treated as empty."""
        from redictum import VolumeController
        vc = VolumeController(volume_level=30)

        tmp_lock.write_text("not json at all {{{")

        fake_run, calls = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()

        data = json.loads(tmp_lock.read_text())
        assert data["volume"] == 50
        assert vc._active is True


# -- Thread safety -----------------------------------------------------------

class TestThreadSafety:
    """Concurrent reduce/restore calls must not corrupt state."""

    def test_concurrent_reduce_restore(self, tmp_lock, monkeypatch):
        """8 threads calling reduce()/restore() must not crash."""
        from redictum import VolumeController
        vc = VolumeController(volume_level=30)

        fake_run, _ = _fake_pactl(50)
        monkeypatch.setattr("subprocess.run", fake_run)
        barrier = threading.Barrier(8)
        errors = []

        def worker():
            try:
                barrier.wait(timeout=5)
                vc.reduce()
                vc.restore()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        assert vc._active is False
