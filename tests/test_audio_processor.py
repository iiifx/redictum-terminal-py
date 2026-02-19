"""Tests for AudioProcessor."""
from __future__ import annotations

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
