"""Tests for AudioRecorder, AudioRecorderBackend ABC, and ArecordRecorder."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def recorder(tmp_path):
    from redictum import ArecordRecorder, AudioRecorder

    backend = ArecordRecorder(device="pulse")
    return AudioRecorder(tmp_path, backend)


# ── AudioRecorderBackend ABC ─────────────────────────────────────────


class TestAudioRecorderBackendABC:
    """AudioRecorderBackend cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        from redictum import AudioRecorderBackend

        with pytest.raises(TypeError):
            AudioRecorderBackend()  # type: ignore[abstract]

    def test_subclass_must_implement_all(self):
        from redictum import AudioRecorderBackend

        class Incomplete(AudioRecorderBackend):
            def start(self, output_path):
                pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


# ── ArecordRecorder unit tests ───────────────────────────────────────


class TestArecordRecorder:
    """ArecordRecorder: arecord subprocess management."""

    def test_start_calls_popen(self, tmp_path, monkeypatch):
        from redictum import ArecordRecorder

        mock_popen = MagicMock()
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        backend = ArecordRecorder(device="pulse")
        out = tmp_path / "test.wav"
        backend.start(out)
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "arecord"
        assert "-D" in args
        assert "pulse" in args
        assert str(out) in args

    def test_stop_returns_exit_code(self, tmp_path, monkeypatch):
        from redictum import ArecordRecorder

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        backend = ArecordRecorder(device="pulse")
        backend.start(tmp_path / "test.wav")
        rc = backend.stop()
        assert rc == 0
        mock_proc.terminate.assert_called_once()

    def test_stop_returns_none_when_not_started(self):
        from redictum import ArecordRecorder

        backend = ArecordRecorder(device="pulse")
        assert backend.stop() is None

    def test_stop_kills_on_timeout(self, tmp_path, monkeypatch):
        from redictum import ArecordRecorder

        mock_proc = MagicMock()
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired("arecord", 5), None]
        mock_proc.returncode = -9
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        backend = ArecordRecorder(device="pulse")
        backend.start(tmp_path / "test.wav")
        rc = backend.stop()
        assert rc == -9
        mock_proc.kill.assert_called_once()

    def test_cancel_terminates(self, tmp_path, monkeypatch):
        from redictum import ArecordRecorder

        mock_proc = MagicMock()
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        backend = ArecordRecorder(device="pulse")
        backend.start(tmp_path / "test.wav")
        backend.cancel()
        mock_proc.terminate.assert_called_once()

    def test_cancel_noop_when_not_started(self):
        from redictum import ArecordRecorder

        backend = ArecordRecorder(device="pulse")
        backend.cancel()  # no error


# ── AudioRecorder integration tests (via ArecordRecorder) ────────────


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
        mock_proc.returncode = 0
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
        mock_proc.returncode = 0
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
