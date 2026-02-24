"""Tests for HotkeyListener runtime: press/release handling, mode resolution."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def make_listener():
    """Factory: create a HotkeyListener without starting pynput."""
    from redictum import HotkeyListener

    def _make(hotkey="Insert", hold_delay=0.3, translate_key=""):
        return HotkeyListener(hotkey, hold_delay, translate_key)

    return _make


@pytest.fixture()
def started_listener(make_listener, monkeypatch):
    """Return a listener with pynput.Listener mocked (no real keyboard)."""

    listener = make_listener(hotkey="Insert", hold_delay=0.1, translate_key="ctrl+Insert")

    # Mock pynput.keyboard.Listener to capture on_press/on_release callbacks
    mock_pynput_listener = MagicMock()
    monkeypatch.setattr("pynput.keyboard.Listener", lambda **kw: mock_pynput_listener)

    on_hold = MagicMock()
    on_release = MagicMock()
    listener.start(on_hold, on_release)

    return listener, on_hold, on_release


# -- _on_press() -------------------------------------------------------------

class TestOnPress:
    """HotkeyListener._on_press: start hold timer or track modifiers."""

    def test_starts_hold_timer(self, started_listener):
        """Pressing target key starts a hold timer."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.insert)
        assert listener._hold_timer is not None
        assert listener._hold_timer.is_alive()
        listener.stop()

    def test_ignores_non_target_key(self, started_listener):
        """Pressing a non-target key does nothing."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.f1)
        assert listener._hold_timer is None

    def test_tracks_modifier_keys(self, started_listener):
        """Modifier keys are tracked in _held_mods."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.ctrl_l)
        assert Key.ctrl_l in listener._held_mods

    def test_ignores_when_already_holding(self, started_listener):
        """Duplicate press while holding is ignored."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.insert)
        first_timer = listener._hold_timer
        listener._on_press(Key.insert)
        # Same timer, not replaced
        assert listener._hold_timer is first_timer
        listener.stop()


# -- _fire_hold() ------------------------------------------------------------

class TestFireHold:
    """HotkeyListener._fire_hold: trigger callback after delay."""

    def test_calls_on_hold(self, started_listener):
        """_fire_hold() calls on_hold with pending mode."""
        listener, on_hold, on_release = started_listener

        listener._pending_mode = "transcribe"
        listener._fire_hold()

        assert listener._is_holding is True
        assert listener._hold_timer is None
        on_hold.assert_called_once_with("transcribe")

    def test_hold_timer_fires(self, started_listener):
        """Hold timer fires after delay and calls on_hold."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.insert)
        time.sleep(0.3)  # hold_delay=0.1 + generous margin
        on_hold.assert_called_once_with("transcribe")
        listener.stop()


# -- _on_key_release() -------------------------------------------------------

class TestOnKeyRelease:
    """HotkeyListener._on_key_release: cancel timer or trigger on_release."""

    def test_early_release_cancels_timer(self, started_listener):
        """Releasing before hold_delay cancels the timer (tap, not hold)."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.insert)
        assert listener._hold_timer is not None
        listener._on_key_release(Key.insert)
        assert listener._hold_timer is None
        on_hold.assert_not_called()
        on_release.assert_not_called()

    def test_release_after_hold_triggers_callback(self, started_listener):
        """Releasing after hold fires on_release with mode."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_press(Key.insert)
        time.sleep(0.3)  # Wait for hold to fire
        listener._on_key_release(Key.insert)

        on_release.assert_called_once_with("transcribe")
        assert listener._is_holding is False

    def test_release_non_target_key_ignored(self, started_listener):
        """Releasing a non-target key does nothing."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._on_key_release(Key.f1)
        on_release.assert_not_called()

    def test_modifier_release_tracked(self, started_listener):
        """Releasing a modifier removes it from _held_mods."""
        from pynput.keyboard import Key
        listener, on_hold, on_release = started_listener

        listener._held_mods.add(Key.ctrl_l)
        listener._on_key_release(Key.ctrl_l)
        assert Key.ctrl_l not in listener._held_mods


# -- _resolve_mode() ---------------------------------------------------------

class TestResolveMode:
    """HotkeyListener._resolve_mode: determine transcribe/translate/None."""

    def test_transcribe_mode(self, started_listener):
        """Target key without translate mods → transcribe."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        mode = listener._resolve_mode(Key.insert)
        assert mode == "transcribe"

    def test_translate_mode(self, started_listener):
        """Target key + ctrl held → translate (higher priority)."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        listener._held_mods.add(Key.ctrl_l)
        mode = listener._resolve_mode(Key.insert)
        assert mode == "translate"

    def test_no_mode(self, started_listener):
        """Non-target key → None."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        mode = listener._resolve_mode(Key.f1)
        assert mode is None


# -- _mods_match() -----------------------------------------------------------

class TestModsMatch:
    """HotkeyListener._mods_match: exact modifier group matching."""

    def test_exact_match(self, started_listener):
        """Required ctrl + held ctrl → match."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        listener._held_mods = {Key.ctrl_l}
        required = frozenset({Key.ctrl_l, Key.ctrl_r})
        assert listener._mods_match(required) is True

    def test_no_match_wrong_modifier(self, started_listener):
        """Required ctrl + held alt → no match."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        listener._held_mods = {Key.alt_l}
        required = frozenset({Key.ctrl_l, Key.ctrl_r})
        assert listener._mods_match(required) is False

    def test_no_match_extra_modifier(self, started_listener):
        """Required none + held ctrl → no match (extra modifier)."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        listener._held_mods = {Key.ctrl_l}
        required = frozenset()
        assert listener._mods_match(required) is False

    def test_empty_match(self, started_listener):
        """No required mods + no held mods → match."""
        listener, _, _ = started_listener

        listener._held_mods = set()
        assert listener._mods_match(frozenset()) is True


# -- stop() ------------------------------------------------------------------

class TestStop:
    """HotkeyListener.stop: cancel timer and stop pynput listener."""

    def test_cancels_timer(self, started_listener):
        """stop() cancels any pending hold timer."""
        from pynput.keyboard import Key
        listener, _, _ = started_listener

        listener._on_press(Key.insert)
        assert listener._hold_timer is not None
        listener.stop()
        assert listener._hold_timer is None

    def test_stops_pynput_listener(self, started_listener):
        """stop() calls listener.stop() on pynput."""
        listener, _, _ = started_listener
        pynput_listener = listener._listener
        listener.stop()
        pynput_listener.stop.assert_called_once()
        assert listener._listener is None

    def test_stop_idempotent(self, started_listener):
        """stop() can be called multiple times safely."""
        listener, _, _ = started_listener
        listener.stop()
        listener.stop()  # Should not raise
