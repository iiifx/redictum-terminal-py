"""Tests for AudioRecorder."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def recorder(tmp_path):
    from redictum import AudioRecorder

    return AudioRecorder(tmp_path, device="pulse")


class TestStart:
    """AudioRecorder.start: launches arecord with correct args."""

    def test_starts_arecord(self, recorder, monkeypatch):
        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        recorder.start()
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "arecord"
        assert "-D" in args
        assert "pulse" in args
        assert "16000" in args


class TestStop:
    """AudioRecorder.stop: terminate and return path."""

    def test_returns_path(self, recorder, monkeypatch, tmp_path):
        mock_proc = MagicMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock()
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)

        recorder.start()
        # Simulate recorded file with some content
        wav_path = recorder._current_file
        wav_path.write_bytes(b"RIFF" + b"\x00" * 100)

        result = recorder.stop()
        assert result is not None
        assert result.suffix == ".wav"
        mock_proc.terminate.assert_called_once()

    def test_returns_none_for_empty_file(self, recorder, monkeypatch, tmp_path):
        mock_proc = MagicMock()
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        recorder.start()
        # File exists but is empty
        recorder._current_file.write_bytes(b"")
        result = recorder.stop()
        assert result is None

    def test_returns_none_when_not_started(self, recorder):
        assert recorder.stop() is None


class TestCancel:
    """AudioRecorder.cancel: terminate and delete."""

    def test_cancel_deletes_file(self, recorder, monkeypatch, tmp_path):
        mock_proc = MagicMock()
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        recorder.start()
        wav_path = recorder._current_file
        wav_path.write_bytes(b"RIFF" + b"\x00" * 100)
        recorder.cancel()
        assert not wav_path.exists()
        mock_proc.terminate.assert_called_once()

    def test_cancel_noop_when_not_started(self, recorder):
        recorder.cancel()  # no error
