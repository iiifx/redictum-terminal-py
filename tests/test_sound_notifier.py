"""Tests for SoundNotifier."""
from __future__ import annotations

import struct
import threading

import pytest


class TestEnsureTonesThreadSafety:
    """SoundNotifier._ensure_tones: thread-safe lazy initialization."""

    def test_concurrent_ensure_creates_single_temp_dir(self, tmp_path, monkeypatch):
        """Multiple threads calling _ensure_tones must create exactly one temp dir."""
        from redictum import SoundNotifier

        tones_dir = tmp_path / "tones"
        tones_dir.mkdir()

        monkeypatch.setattr(
            "tempfile.mkdtemp",
            lambda prefix="": str(tones_dir),
        )

        notifier = SoundNotifier(volume=30)
        barrier = threading.Barrier(4)
        errors = []

        def worker():
            try:
                barrier.wait(timeout=5)
                notifier._ensure_tones()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        # _sounds must be populated (all 4 tones)
        assert len(notifier._sounds) == 4

    def test_init_lock_exists(self):
        """SoundNotifier must have _init_lock for thread-safe initialization."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=30)
        assert hasattr(notifier, "_init_lock")
        assert isinstance(notifier._init_lock, type(threading.Lock()))


class TestWriteWav:
    """SoundNotifier._write_wav: produces valid WAV header."""

    def test_wav_header(self, tmp_path, monkeypatch):
        from redictum import SoundNotifier

        # Prevent __init__ from generating all tones (slow)
        monkeypatch.setattr("redictum._generate_tones", lambda: {})
        notifier = SoundNotifier.__new__(SoundNotifier)
        notifier._temp_dir = tmp_path
        notifier._sounds = {}

        samples = [0.5, -0.3, 0.1, 0.0]
        path = notifier._write_wav("test.wav", samples)

        data = path.read_bytes()
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"
        # File size in RIFF header = 36 + data bytes
        riff_size = struct.unpack("<I", data[4:8])[0]
        pcm_len = len(samples) * 2  # 16-bit = 2 bytes per sample
        assert riff_size == 36 + pcm_len


class TestGenerateTones:
    """_generate_tones: produces 4 named tone lists."""

    def test_four_keys(self):
        from redictum import _generate_tones

        tones = _generate_tones()
        assert set(tones.keys()) == {"start", "processing", "done", "error"}

    def test_nonempty_float_lists(self):
        from redictum import _generate_tones

        for name, samples in _generate_tones().items():
            assert len(samples) > 0
            assert all(isinstance(s, float) for s in samples)
