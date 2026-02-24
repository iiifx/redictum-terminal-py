"""Tests for VolumeController: reduce/restore volume via pactl."""
from __future__ import annotations

import subprocess
import threading
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def vc():
    from redictum import VolumeController
    return VolumeController(volume_level=30)


# -- reduce() ---------------------------------------------------------------

class TestReduce:
    """VolumeController.reduce(): save current volume and lower it."""

    def test_normal_path(self, vc, monkeypatch):
        """reduce() reads current volume and sets target = current * level / 100."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            result = MagicMock()
            result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()

        assert len(calls) == 2
        # get-sink-volume
        assert calls[0][1] == "get-sink-volume"
        # set-sink-volume with target = 50 * 30 / 100 = 15
        assert calls[1] == ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "15%"]
        assert vc._saved_volume == "50%"

    def test_guard_repeated_call(self, vc, monkeypatch):
        """reduce() is a no-op when already reduced (saved_volume not None)."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            result = MagicMock()
            result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        count_after_first = len(calls)
        vc.reduce()
        # No additional calls — guard returned early
        assert len(calls) == count_after_first

    def test_pactl_not_found(self, vc, monkeypatch):
        """reduce() silently skips when pactl is not installed."""
        def fake_run(cmd, **kw):
            raise FileNotFoundError("pactl")

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._saved_volume is None

    def test_timeout(self, vc, monkeypatch):
        """reduce() silently skips on timeout."""
        def fake_run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 2)

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._saved_volume is None

    def test_unparsable_output(self, vc, monkeypatch):
        """reduce() skips when pactl output doesn't contain volume percentage."""
        def fake_run(cmd, **kw):
            result = MagicMock()
            result.stdout = "no volume info here"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        assert vc._saved_volume is None

    def test_set_volume_failure(self, vc, monkeypatch):
        """reduce() saves volume even if set-sink-volume fails."""
        call_count = [0]

        def fake_run(cmd, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                # get-sink-volume succeeds
                result = MagicMock()
                result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
                return result
            # set-sink-volume fails
            raise FileNotFoundError("pactl")

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        # Volume was saved even though set failed
        assert vc._saved_volume == "50%"

    def test_relative_calculation(self, monkeypatch):
        """Target volume is relative to current: volume_level=30, current=80% → 24%."""
        from redictum import VolumeController
        vc = VolumeController(volume_level=30)
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            result = MagicMock()
            result.stdout = "Volume: front-left: 52428 /  80% / -5.81 dB"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        # target = 80 * 30 / 100 = 24
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

    def test_normal_path(self, vc, monkeypatch):
        """restore() calls set-sink-volume with saved percentage."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            result = MagicMock()
            result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        calls.clear()
        vc.restore()
        assert calls == [["pactl", "set-sink-volume", "@DEFAULT_SINK@", "50%"]]
        assert vc._saved_volume is None

    def test_guard_no_saved(self, vc, monkeypatch):
        """restore() is a no-op when there is no saved volume."""
        calls = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: calls.append(a))
        vc.restore()
        assert calls == []

    def test_idempotent(self, vc, monkeypatch):
        """restore() can be called multiple times safely."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            result = MagicMock()
            result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        vc.reduce()
        calls.clear()
        vc.restore()
        vc.restore()
        vc.restore()
        # Only one restore call — second/third are no-ops
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
        # saved_volume was cleared even though restore failed
        assert vc._saved_volume is None


# -- Thread safety -----------------------------------------------------------

class TestThreadSafety:
    """Concurrent reduce/restore calls must not corrupt state."""

    def test_concurrent_reduce_restore(self, monkeypatch):
        """8 threads calling reduce()/restore() must not corrupt state."""
        from redictum import VolumeController
        vc = VolumeController(volume_level=30)

        def fake_run(cmd, **kw):
            result = MagicMock()
            result.stdout = "Volume: front-left: 32768 /  50% / -18.06 dB"
            return result

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
        # Final state: saved_volume should be None (all restored)
        assert vc._saved_volume is None
