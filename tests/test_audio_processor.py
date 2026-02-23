"""Tests for AudioProcessor."""
from __future__ import annotations

import struct
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def processor():
    from redictum import AudioProcessor

    return AudioProcessor()


class TestNormalize:
    """AudioProcessor.normalize: ffmpeg wrapper."""

    def test_success_returns_norm_path(self, processor, monkeypatch, tmp_path):
        input_path = tmp_path / "rec_001.wav"
        input_path.write_text("x")

        def fake_run(cmd, **kwargs):
            # Create the output file to simulate ffmpeg
            out = tmp_path / "rec_001_norm.wav"
            out.write_text("normalized")
            r = MagicMock()
            r.returncode = 0
            r.stderr = b""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        result = processor.normalize(input_path)
        assert result.stem == "rec_001_norm"
        assert result.suffix == ".wav"

    def test_failure_raises(self, processor, monkeypatch, tmp_path):
        from redictum import RedictumError

        input_path = tmp_path / "rec.wav"
        input_path.write_text("x")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stderr = b"error details"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        with pytest.raises(RedictumError, match="ffmpeg normalization failed"):
            processor.normalize(input_path)

    def test_timeout_raises(self, processor, monkeypatch, tmp_path):
        from redictum import RedictumError

        input_path = tmp_path / "rec.wav"
        input_path.write_text("x")

        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 60)

        monkeypatch.setattr("subprocess.run", fake_run)
        with pytest.raises(RedictumError, match="timed out"):
            processor.normalize(input_path)


def _build_wav(chunks: list[tuple[bytes, bytes]]) -> bytes:
    """Build a WAV file from a list of (chunk_id, chunk_data) pairs."""
    body = b""
    for chunk_id, chunk_data in chunks:
        body += chunk_id + struct.pack("<I", len(chunk_data)) + chunk_data
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body


def _pcm_samples(*values: int) -> bytes:
    """Pack signed 16-bit samples into raw PCM bytes."""
    return struct.pack(f"<{len(values)}h", *values)


class TestHasSpeech:
    """AudioProcessor.has_speech: WAV chunk parsing and RMS calculation."""

    def test_standard_44byte_header(self, tmp_path):
        """Standard WAV with 44-byte header (fmt + data) works correctly."""
        from redictum import AudioProcessor

        pcm = _pcm_samples(1000, -1000, 1000, -1000)
        fmt_data = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
        wav = _build_wav([(b"fmt ", fmt_data), (b"data", pcm)])

        path = tmp_path / "test.wav"
        path.write_bytes(wav)
        # RMS of [1000, -1000, 1000, -1000] = 1000 > default threshold 200
        assert AudioProcessor.has_speech(path) is True

    def test_extra_chunks_before_data(self, tmp_path):
        """WAV with LIST/INFO chunks before data is parsed correctly."""
        from redictum import AudioProcessor

        pcm = _pcm_samples(5000, -5000, 5000, -5000)
        fmt_data = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
        list_data = b"INFOsome metadata here"
        junk_data = b"\x00" * 64
        wav = _build_wav([
            (b"fmt ", fmt_data),
            (b"LIST", list_data),
            (b"JUNK", junk_data),
            (b"data", pcm),
        ])

        path = tmp_path / "extra_chunks.wav"
        path.write_bytes(wav)
        assert AudioProcessor.has_speech(path) is True

    def test_silence_below_threshold(self, tmp_path):
        """Silent audio (low RMS) returns False."""
        from redictum import AudioProcessor

        pcm = _pcm_samples(10, -10, 5, -5, 10, -10)
        fmt_data = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
        wav = _build_wav([(b"fmt ", fmt_data), (b"data", pcm)])

        path = tmp_path / "silence.wav"
        path.write_bytes(wav)
        # RMS ≈ 8.5 < threshold 200
        assert AudioProcessor.has_speech(path) is False

    def test_not_a_wav_file(self, tmp_path):
        """Non-WAV file returns False (no crash)."""
        from redictum import AudioProcessor

        path = tmp_path / "garbage.wav"
        path.write_bytes(b"this is not a wav file at all")
        assert AudioProcessor.has_speech(path) is False

    def test_empty_data_chunk(self, tmp_path):
        """WAV with empty data chunk returns False."""
        from redictum import AudioProcessor

        fmt_data = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
        wav = _build_wav([(b"fmt ", fmt_data), (b"data", b"")])

        path = tmp_path / "empty.wav"
        path.write_bytes(wav)
        assert AudioProcessor.has_speech(path) is False

    def test_custom_threshold(self, tmp_path):
        """Custom threshold is respected."""
        from redictum import AudioProcessor

        pcm = _pcm_samples(300, -300, 300, -300)
        fmt_data = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
        wav = _build_wav([(b"fmt ", fmt_data), (b"data", pcm)])

        path = tmp_path / "custom.wav"
        path.write_bytes(wav)
        # RMS = 300
        assert AudioProcessor.has_speech(path, threshold=200) is True
        assert AudioProcessor.has_speech(path, threshold=400) is False
