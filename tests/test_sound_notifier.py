"""Tests for SoundNotifier."""
from __future__ import annotations

import struct
import threading
from unittest.mock import MagicMock


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

        for _name, samples in _generate_tones().items():
            assert len(samples) > 0
            assert all(isinstance(s, float) for s in samples)


# -- _play() ----------------------------------------------------------------

class TestPlay:
    """SoundNotifier._play: Popen call and error handling."""

    def test_play_calls_paplay(self, tmp_path, monkeypatch):
        """_play() invokes paplay with correct volume and wav path."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=50)
        # Pre-populate sounds to skip _ensure_tones
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)

        notifier._play("start")

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "paplay"
        # volume=50 → 50/100 * 65536 = 32768
        assert args[1] == "--volume=32768"
        assert args[2] == str(wav)

    def test_wav_not_found(self, tmp_path, monkeypatch):
        """_play() silently returns when wav file is missing."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=30)
        notifier._sounds = {"start": tmp_path / "nonexistent.wav"}
        notifier._temp_dir = tmp_path

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        notifier._play("start")
        mock_popen.assert_not_called()

    def test_paplay_not_found_warns_once(self, tmp_path, monkeypatch, caplog):
        """_play() warns once when paplay is not found."""
        import logging

        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=30)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        monkeypatch.setattr("subprocess.Popen", MagicMock(side_effect=FileNotFoundError))

        with caplog.at_level(logging.WARNING):
            notifier._play("start")
            notifier._play("start")

        assert notifier._warned_no_paplay is True
        warning_count = sum(1 for r in caplog.records if "paplay not found" in r.message)
        assert warning_count == 1

    def test_unknown_sound_name(self, tmp_path, monkeypatch):
        """_play() silently returns for unknown sound name."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=30)
        notifier._sounds = {}
        notifier._temp_dir = tmp_path

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        notifier._play("nonexistent")
        mock_popen.assert_not_called()


# -- cleanup() ---------------------------------------------------------------

class TestCleanup:
    """SoundNotifier.cleanup: remove temp directory."""

    def test_removes_temp_dir(self, tmp_path):
        """cleanup() removes the temp directory."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=30)
        tones_dir = tmp_path / "tones"
        tones_dir.mkdir()
        (tones_dir / "test.wav").write_bytes(b"data")
        notifier._temp_dir = tones_dir

        notifier.cleanup()
        assert not tones_dir.exists()

    def test_safe_when_none(self):
        """cleanup() is safe when _temp_dir is None."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=30)
        assert notifier._temp_dir is None
        notifier.cleanup()  # Should not raise


# -- Volume scaling ----------------------------------------------------------

class TestVolumeScaling:
    """Volume percentage to paplay volume scaling."""

    def test_volume_50_percent(self, tmp_path, monkeypatch):
        """volume=50 → 32768."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=50)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        notifier._play("start")
        assert mock_popen.call_args[0][0][1] == "--volume=32768"

    def test_volume_0_percent(self, tmp_path, monkeypatch):
        """volume=0 → 0."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=0)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        notifier._play("start")
        assert mock_popen.call_args[0][0][1] == "--volume=0"

    def test_volume_100_percent(self, tmp_path, monkeypatch):
        """volume=100 → 65536."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(volume=100)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        notifier._play("start")
        assert mock_popen.call_args[0][0][1] == "--volume=65536"
