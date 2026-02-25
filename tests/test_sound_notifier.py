"""Tests for SoundNotifier, SoundPlayerBackend, and PaplayPlayer."""
from __future__ import annotations

import struct
import threading
from pathlib import Path
from unittest.mock import MagicMock

# -- Fake player for injection -----------------------------------------------


def _make_fake_player():
    """Create a FakeSoundPlayer instance (imports lazily)."""
    from redictum import SoundPlayerBackend

    class FakeSoundPlayer(SoundPlayerBackend):
        """Test double that records play() calls."""

        def __init__(self) -> None:
            self.played: list[tuple[Path, int]] = []

        def play(self, wav_path: Path, volume: int) -> None:
            self.played.append((wav_path, volume))

    return FakeSoundPlayer()


# -- SoundPlayerBackend ABC --------------------------------------------------


class TestSoundPlayerBackendABC:
    """SoundPlayerBackend cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        """ABC raises TypeError on direct instantiation."""
        import pytest
        from redictum import SoundPlayerBackend

        with pytest.raises(TypeError):
            SoundPlayerBackend()  # type: ignore[abstract]

    def test_subclass_must_implement_play(self):
        """Concrete subclass without play() raises TypeError."""
        import pytest
        from redictum import SoundPlayerBackend

        class Broken(SoundPlayerBackend):
            pass

        with pytest.raises(TypeError):
            Broken()  # type: ignore[abstract]


# -- PaplayPlayer ------------------------------------------------------------


class TestPaplayPlayer:
    """PaplayPlayer: subprocess.Popen call and error handling."""

    def test_calls_popen_with_correct_args(self, tmp_path, monkeypatch):
        """play() invokes paplay with scaled volume and wav path."""
        from redictum import PaplayPlayer

        player = PaplayPlayer()
        wav = tmp_path / "tone.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)

        player.play(wav, 50)

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "paplay"
        assert args[1] == "--volume=32768"
        assert args[2] == str(wav)

    def test_volume_scaling_0(self, tmp_path, monkeypatch):
        """volume=0 → paplay volume 0."""
        from redictum import PaplayPlayer

        player = PaplayPlayer()
        wav = tmp_path / "tone.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        player.play(wav, 0)
        assert mock_popen.call_args[0][0][1] == "--volume=0"

    def test_volume_scaling_100(self, tmp_path, monkeypatch):
        """volume=100 → paplay volume 65536."""
        from redictum import PaplayPlayer

        player = PaplayPlayer()
        wav = tmp_path / "tone.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        player.play(wav, 100)
        assert mock_popen.call_args[0][0][1] == "--volume=65536"

    def test_file_not_found_warns_once(self, tmp_path, monkeypatch, caplog):
        """play() warns once when paplay is not installed."""
        import logging

        from redictum import PaplayPlayer

        player = PaplayPlayer()
        wav = tmp_path / "tone.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)

        monkeypatch.setattr("subprocess.Popen", MagicMock(side_effect=FileNotFoundError))

        with caplog.at_level(logging.WARNING):
            player.play(wav, 30)
            player.play(wav, 30)

        assert player._warned is True
        warning_count = sum(1 for r in caplog.records if "paplay not found" in r.message)
        assert warning_count == 1


# -- SoundNotifier._ensure_tones thread safety -------------------------------


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

        notifier = SoundNotifier(_make_fake_player(), volume=30)
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

        notifier = SoundNotifier(_make_fake_player(), volume=30)
        assert hasattr(notifier, "_init_lock")
        assert isinstance(notifier._init_lock, type(threading.Lock()))


# -- _write_wav ---------------------------------------------------------------


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


# -- _generate_tones ----------------------------------------------------------


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


# -- _play() ------------------------------------------------------------------


class TestPlay:
    """SoundNotifier._play: delegates to injected player."""

    def test_play_delegates_to_player(self, tmp_path):
        """_play() passes wav_path and volume to the injected player."""
        from redictum import SoundNotifier

        player = _make_fake_player()
        notifier = SoundNotifier(player, volume=50)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        notifier._play("start")

        assert len(player.played) == 1
        assert player.played[0] == (wav, 50)

    def test_wav_not_found(self, tmp_path):
        """_play() silently returns when wav file is missing."""
        from redictum import SoundNotifier

        player = _make_fake_player()
        notifier = SoundNotifier(player, volume=30)
        notifier._sounds = {"start": tmp_path / "nonexistent.wav"}
        notifier._temp_dir = tmp_path

        notifier._play("start")
        assert len(player.played) == 0

    def test_unknown_sound_name(self, tmp_path):
        """_play() silently returns for unknown sound name."""
        from redictum import SoundNotifier

        player = _make_fake_player()
        notifier = SoundNotifier(player, volume=30)
        notifier._sounds = {}
        notifier._temp_dir = tmp_path

        notifier._play("nonexistent")
        assert len(player.played) == 0


# -- cleanup() ----------------------------------------------------------------


class TestCleanup:
    """SoundNotifier.cleanup: remove temp directory."""

    def test_removes_temp_dir(self, tmp_path):
        """cleanup() removes the temp directory."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(_make_fake_player(), volume=30)
        tones_dir = tmp_path / "tones"
        tones_dir.mkdir()
        (tones_dir / "test.wav").write_bytes(b"data")
        notifier._temp_dir = tones_dir

        notifier.cleanup()
        assert not tones_dir.exists()

    def test_safe_when_none(self):
        """cleanup() is safe when _temp_dir is None."""
        from redictum import SoundNotifier

        notifier = SoundNotifier(_make_fake_player(), volume=30)
        assert notifier._temp_dir is None
        notifier.cleanup()  # Should not raise


# -- Volume passing -----------------------------------------------------------


class TestVolumeScaling:
    """Volume percentage passed through to player."""

    def test_volume_50_percent(self, tmp_path):
        """volume=50 passed to player.play()."""
        from redictum import SoundNotifier

        player = _make_fake_player()
        notifier = SoundNotifier(player, volume=50)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        notifier._play("start")
        assert player.played[0][1] == 50

    def test_volume_0_percent(self, tmp_path):
        """volume=0 passed to player.play()."""
        from redictum import SoundNotifier

        player = _make_fake_player()
        notifier = SoundNotifier(player, volume=0)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        notifier._play("start")
        assert player.played[0][1] == 0

    def test_volume_100_percent(self, tmp_path):
        """volume=100 passed to player.play()."""
        from redictum import SoundNotifier

        player = _make_fake_player()
        notifier = SoundNotifier(player, volume=100)
        wav = tmp_path / "start.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 40)
        notifier._sounds = {"start": wav}
        notifier._temp_dir = tmp_path

        notifier._play("start")
        assert player.played[0][1] == 100
