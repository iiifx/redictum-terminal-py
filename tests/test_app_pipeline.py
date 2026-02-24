"""Tests for RedictumApp: _on_hold, _run_pipeline, _graceful_shutdown."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock


def _make_app(tmp_path, **overrides):
    """Build a RedictumApp with all components mocked out.

    Returns (app, mocks_dict) so tests can inspect calls to individual mocks.
    """
    from redictum import STATE_IDLE, RedictumApp

    app = RedictumApp.__new__(RedictumApp)

    # State machine
    app._state = STATE_IDLE
    app._state_lock = threading.Lock()
    app._pipeline_done = threading.Event()
    app._pipeline_done.set()
    app._current_mode = "transcribe"

    # Config sections
    app._audio_cfg = {
        "recording_device": "default",
        "recording_silence_detection": True,
        "recording_silence_threshold": 200,
        "recording_normalize": True,
        "recording_volume_reduce": True,
        "recording_volume_level": 30,
    }
    app._clip_cfg = {
        "paste_auto": True,
        "paste_prefix": "",
        "paste_postfix": " ",
        "paste_restore_delay": 0.0,
    }
    app._sound_cfg = {
        "sound_signal_start": True,
        "sound_signal_processing": False,
        "sound_signal_done": True,
        "sound_signal_error": True,
        "sound_signal_volume": 30,
    }
    app._transcripts_dir = tmp_path / "transcripts"
    app._transcripts_dir.mkdir()

    # Component mocks
    mocks = {}
    for name in ("_recorder", "_processor", "_transcriber",
                 "_clipboard", "_notifier", "_volume_ctl", "_housekeeper"):
        m = MagicMock()
        setattr(app, name, m)
        mocks[name] = m

    # Defaults for happy path
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"\x00" * 1000)
    mocks["_recorder"].stop.return_value = audio_file
    mocks["_processor"].has_speech.return_value = True
    mocks["_processor"].normalize.return_value = audio_file
    mocks["_transcriber"].transcribe.return_value = "hello world"
    mocks["_clipboard"].save.return_value = {"text": "old"}

    # Apply test overrides
    for key, value in overrides.items():
        if key.startswith("_") and key in mocks:
            continue
        if "." in key:
            section, k = key.split(".", 1)
            getattr(app, section)[k] = value
        else:
            setattr(app, key, value)

    return app, mocks


# =============================================================================
# _on_hold()
# =============================================================================

class TestOnHold:
    """RedictumApp._on_hold: IDLE → RECORDING transition."""

    def test_idle_to_recording(self, tmp_path):
        """_on_hold transitions from IDLE to RECORDING."""
        from redictum import STATE_RECORDING
        app, mocks = _make_app(tmp_path)
        app._on_hold("transcribe")
        assert app._state == STATE_RECORDING
        mocks["_recorder"].start.assert_called_once()

    def test_ignores_if_not_idle(self, tmp_path):
        """_on_hold is a no-op when state is not IDLE."""
        from redictum import STATE_RECORDING
        app, mocks = _make_app(tmp_path)
        app._state = STATE_RECORDING
        app._on_hold("transcribe")
        mocks["_recorder"].start.assert_not_called()

    def test_start_sound_enabled(self, tmp_path):
        """_on_hold plays start sound when enabled."""
        app, mocks = _make_app(tmp_path)
        app._on_hold("transcribe")
        mocks["_notifier"].play_start.assert_called_once()

    def test_start_sound_disabled(self, tmp_path):
        """_on_hold skips start sound when disabled."""
        app, mocks = _make_app(tmp_path)
        app._sound_cfg["sound_signal_start"] = False
        app._on_hold("transcribe")
        mocks["_notifier"].play_start.assert_not_called()

    def test_recorder_start_fails_returns_to_idle(self, tmp_path):
        """_on_hold returns to IDLE if recorder.start() raises."""
        from redictum import STATE_IDLE
        app, mocks = _make_app(tmp_path)
        mocks["_recorder"].start.side_effect = RuntimeError("mic busy")
        app._on_hold("transcribe")
        assert app._state == STATE_IDLE
        mocks["_notifier"].play_error.assert_called_once()

    def test_volume_reduce_called(self, tmp_path, monkeypatch):
        """_on_hold calls VolumeController.reduce() after play_start."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        app._on_hold("transcribe")
        mocks["_volume_ctl"].reduce.assert_called_once()

    def test_volume_reduce_skipped_when_disabled(self, tmp_path):
        """_on_hold skips volume reduce when volume_ctl is None."""
        app, mocks = _make_app(tmp_path)
        app._volume_ctl = None
        app._on_hold("transcribe")
        # Should not raise — volume_ctl is None


# =============================================================================
# _run_pipeline()
# =============================================================================

class TestRunPipeline:
    """RedictumApp._run_pipeline: full processing path."""

    def test_full_success_path(self, tmp_path, monkeypatch):
        """Full pipeline: stop → restore → transcribe → paste → done."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_IDLE, STATE_PROCESSING
        app._state = STATE_PROCESSING

        app._run_pipeline("transcribe")

        mocks["_recorder"].stop.assert_called_once()
        mocks["_volume_ctl"].restore.assert_called()
        mocks["_transcriber"].transcribe.assert_called_once()
        mocks["_clipboard"].copy.assert_called_once()
        mocks["_clipboard"].paste.assert_called_once()
        mocks["_notifier"].play_stop.assert_called_once()
        mocks["_housekeeper"].rotate_audio.assert_called_once()
        assert app._state == STATE_IDLE
        assert app._pipeline_done.is_set()

    def test_recorder_stop_returns_none(self, tmp_path, monkeypatch):
        """Pipeline handles recorder.stop() returning None (no audio)."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_IDLE, STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_recorder"].stop.return_value = None

        app._run_pipeline("transcribe")

        mocks["_notifier"].play_error.assert_called_once()
        mocks["_transcriber"].transcribe.assert_not_called()
        assert app._state == STATE_IDLE

    def test_silence_detection_blocks(self, tmp_path, monkeypatch):
        """Pipeline skips transcription when silence is detected."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_IDLE, STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_processor"].has_speech.return_value = False

        app._run_pipeline("transcribe")

        mocks["_transcriber"].transcribe.assert_not_called()
        assert app._state == STATE_IDLE

    def test_empty_transcription_skips_paste(self, tmp_path, monkeypatch):
        """Pipeline skips paste when transcription is empty."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_transcriber"].transcribe.return_value = ""

        app._run_pipeline("transcribe")

        mocks["_clipboard"].copy.assert_not_called()

    def test_paste_auto_disabled(self, tmp_path, monkeypatch):
        """Pipeline copies but doesn't paste when paste_auto=False."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._clip_cfg["paste_auto"] = False

        app._run_pipeline("transcribe")

        mocks["_clipboard"].copy.assert_called_once()
        mocks["_clipboard"].paste.assert_not_called()
        mocks["_clipboard"].save.assert_not_called()

    def test_prefix_postfix_applied(self, tmp_path, monkeypatch):
        """Pipeline prepends prefix and appends postfix."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._clip_cfg["paste_prefix"] = ">>> "
        app._clip_cfg["paste_postfix"] = " <<<"

        app._run_pipeline("transcribe")

        copied_text = mocks["_clipboard"].copy.call_args[0][0]
        assert copied_text == ">>> hello world <<<"

    def test_translate_mode(self, tmp_path, monkeypatch):
        """Pipeline passes translate=True when mode is 'translate'."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING

        app._run_pipeline("translate")

        mocks["_transcriber"].transcribe.assert_called_once()
        assert mocks["_transcriber"].transcribe.call_args[1]["translate"] is True

    def test_normalize_enabled(self, tmp_path, monkeypatch):
        """Pipeline calls processor.normalize() when enabled."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING

        app._run_pipeline("transcribe")

        mocks["_processor"].normalize.assert_called_once()

    def test_normalize_disabled(self, tmp_path, monkeypatch):
        """Pipeline skips normalize when disabled."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._audio_cfg["recording_normalize"] = False

        app._run_pipeline("transcribe")

        mocks["_processor"].normalize.assert_not_called()

    def test_normalize_fails_fallback(self, tmp_path, monkeypatch):
        """Pipeline falls back to raw audio when normalize() raises."""
        from redictum import RedictumError
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_processor"].normalize.side_effect = RedictumError("ffmpeg failed")

        app._run_pipeline("transcribe")

        # Transcription still called (with original audio path)
        mocks["_transcriber"].transcribe.assert_called_once()

    def test_volume_restored_in_finally(self, tmp_path, monkeypatch):
        """Volume is always restored in finally block, even on error."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_recorder"].stop.side_effect = RuntimeError("crash")

        app._run_pipeline("transcribe")

        mocks["_volume_ctl"].restore.assert_called()

    def test_state_returns_to_idle_on_error(self, tmp_path, monkeypatch):
        """State is always set back to IDLE, even on unexpected error."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_IDLE, STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_recorder"].stop.side_effect = RuntimeError("crash")

        app._run_pipeline("transcribe")

        assert app._state == STATE_IDLE
        assert app._pipeline_done.is_set()

    def test_error_sound_on_exception(self, tmp_path, monkeypatch):
        """Error sound plays on unexpected exception."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_recorder"].stop.side_effect = RuntimeError("crash")

        app._run_pipeline("transcribe")

        mocks["_notifier"].play_error.assert_called()

    def test_pipeline_done_event_set(self, tmp_path, monkeypatch):
        """pipeline_done event is always set after pipeline finishes."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._pipeline_done.clear()

        app._run_pipeline("transcribe")

        assert app._pipeline_done.is_set()

    def test_silence_detection_disabled(self, tmp_path, monkeypatch):
        """Pipeline skips silence check when disabled."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._audio_cfg["recording_silence_detection"] = False

        app._run_pipeline("transcribe")

        mocks["_processor"].has_speech.assert_not_called()
        mocks["_transcriber"].transcribe.assert_called_once()

    def test_processing_sound_enabled(self, tmp_path, monkeypatch):
        """Pipeline plays processing sound when enabled."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._sound_cfg["sound_signal_processing"] = True

        app._run_pipeline("transcribe")

        mocks["_notifier"].play_processing.assert_called_once()

    def test_redictum_error_plays_error_sound(self, tmp_path, monkeypatch):
        """RedictumError in pipeline triggers error sound."""
        from redictum import RedictumError
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        mocks["_transcriber"].transcribe.side_effect = RedictumError("whisper failed")

        app._run_pipeline("transcribe")

        mocks["_notifier"].play_error.assert_called()

    def test_volume_ctl_none_safe(self, tmp_path, monkeypatch):
        """Pipeline runs fine when volume_ctl is None."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr("redictum._log_transcript", lambda *a: None)
        app, mocks = _make_app(tmp_path)
        from redictum import STATE_PROCESSING
        app._state = STATE_PROCESSING
        app._volume_ctl = None

        app._run_pipeline("transcribe")

        mocks["_transcriber"].transcribe.assert_called_once()


# =============================================================================
# _graceful_shutdown()
# =============================================================================

class TestGracefulShutdown:
    """RedictumApp._graceful_shutdown: clean up on exit."""

    def test_idle_stops_listener_and_notifier(self, tmp_path):
        """Shutdown from IDLE stops listener and cleans up notifier."""
        from redictum import STATE_IDLE
        app, mocks = _make_app(tmp_path)
        app._state = STATE_IDLE
        listener = MagicMock()

        app._graceful_shutdown(listener)

        listener.stop.assert_called_once()
        mocks["_notifier"].cleanup.assert_called_once()

    def test_recording_cancels_and_restores_volume(self, tmp_path):
        """Shutdown during RECORDING cancels recording and restores volume."""
        from redictum import STATE_RECORDING
        app, mocks = _make_app(tmp_path)
        app._state = STATE_RECORDING
        listener = MagicMock()

        app._graceful_shutdown(listener)

        mocks["_recorder"].cancel.assert_called_once()
        mocks["_volume_ctl"].restore.assert_called_once()

    def test_processing_waits_for_pipeline(self, tmp_path):
        """Shutdown during PROCESSING waits for pipeline to finish."""
        from redictum import STATE_PROCESSING
        app, mocks = _make_app(tmp_path)
        app._state = STATE_PROCESSING
        app._pipeline_done.clear()
        listener = MagicMock()

        # Set pipeline_done after a short delay to unblock wait
        def set_done():
            time.sleep(0.05)
            app._pipeline_done.set()

        threading.Thread(target=set_done, daemon=True).start()

        app._graceful_shutdown(listener)

        listener.stop.assert_called_once()


# =============================================================================
# Concurrency
# =============================================================================

class TestConcurrency:
    """Concurrent _on_hold calls — recorder.start() exactly once."""

    def test_multiple_on_hold_one_start(self, tmp_path, monkeypatch):
        """5 threads calling _on_hold → recorder.start() exactly 1 time."""
        monkeypatch.setattr("time.sleep", lambda s: None)
        app, mocks = _make_app(tmp_path)
        barrier = threading.Barrier(5)
        errors = []

        def worker():
            try:
                barrier.wait(timeout=5)
                app._on_hold("transcribe")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        mocks["_recorder"].start.assert_called_once()
