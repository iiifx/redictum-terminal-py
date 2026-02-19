"""Tests for SoundNotifier."""
from __future__ import annotations

import struct


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
