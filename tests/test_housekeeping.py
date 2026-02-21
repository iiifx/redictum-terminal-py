"""Tests for Housekeeping."""
from __future__ import annotations

import time
from pathlib import Path


class TestRotate:
    """Housekeeping._rotate: static method for file rotation."""

    def test_excess_files_removed(self, tmp_path):
        from redictum import Housekeeping

        files = []
        for i in range(7):
            f = tmp_path / f"file_{i:02d}.txt"
            f.write_text(f"data {i}")
            time.sleep(0.01)  # ensure different mtime
            files.append(f)
        files.sort(key=lambda p: p.stat().st_mtime)
        removed = Housekeeping._rotate(files, max_files=5, label="Test")
        assert removed == 2
        assert not files[0].exists()
        assert not files[1].exists()
        assert files[2].exists()

    def test_no_excess(self, tmp_path):
        from redictum import Housekeeping

        files = []
        for i in range(3):
            f = tmp_path / f"file_{i}.txt"
            f.write_text("x")
            files.append(f)
        removed = Housekeeping._rotate(files, max_files=5, label="Test")
        assert removed == 0

    def test_empty_list(self):
        from redictum import Housekeeping

        assert Housekeeping._rotate([], max_files=5, label="Test") == 0


class TestRotateAudio:
    """Housekeeping.rotate_audio: rotate all wav including *_norm.wav."""

    def test_includes_norm_files(self, tmp_path):
        from redictum import Housekeeping

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        transcripts_dir = tmp_path / "transcripts"
        transcripts_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Create 4 regular + 2 norm files (6 total)
        for i in range(4):
            (audio_dir / f"rec_{i:02d}.wav").write_text("x")
            time.sleep(0.01)
        (audio_dir / "rec_00_norm.wav").write_text("x")
        (audio_dir / "rec_01_norm.wav").write_text("x")

        hk = Housekeeping(audio_dir, transcripts_dir, logs_dir, {"audio": {"max_files": 2}})
        removed = hk.rotate_audio()
        assert removed == 4
        # Only 2 newest files remain
        assert len(list(audio_dir.glob("*.wav"))) == 2


class TestRotateTranscripts:
    """Housekeeping.rotate_transcripts: remove oldest .txt."""

    def test_removes_oldest(self, tmp_path):
        from redictum import Housekeeping

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        transcripts_dir = tmp_path / "transcripts"
        transcripts_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        for i in range(5):
            (transcripts_dir / f"2025-01-{i+1:02d}.txt").write_text("x")
            time.sleep(0.01)

        hk = Housekeeping(audio_dir, transcripts_dir, logs_dir, {"transcripts": {"max_files": 3}})
        removed = hk.rotate_transcripts()
        assert removed == 2
        remaining = list(transcripts_dir.glob("*.txt"))
        assert len(remaining) == 3


class TestRotateLogs:
    """Housekeeping.rotate_logs: remove oldest .log."""

    def test_removes_oldest(self, tmp_path):
        from redictum import Housekeeping

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        transcripts_dir = tmp_path / "transcripts"
        transcripts_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        for i in range(5):
            (logs_dir / f"redictum_20260220_{i:02d}0000.log").write_text("x")
            time.sleep(0.01)

        hk = Housekeeping(audio_dir, transcripts_dir, logs_dir, {"logs": {"max_files": 2}})
        removed = hk.rotate_logs()
        assert removed == 3
        remaining = list(logs_dir.glob("*.log"))
        assert len(remaining) == 2
