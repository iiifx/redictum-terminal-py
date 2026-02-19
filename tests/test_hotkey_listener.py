"""Tests for HotkeyListener: _parse_key and _parse_combo."""
from __future__ import annotations

import pytest


class TestParseKey:
    """HotkeyListener._parse_key: string → pynput key object."""

    def test_insert(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        result = HotkeyListener._parse_key("Insert")
        assert result == Key.insert

    def test_f12(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        result = HotkeyListener._parse_key("F12")
        assert result == Key.f12

    def test_single_char(self):
        from pynput.keyboard import KeyCode
        from redictum import HotkeyListener

        result = HotkeyListener._parse_key("a")
        assert result == KeyCode.from_char("a")

    def test_unknown_raises(self):
        from redictum import HotkeyListener, RedictumError

        with pytest.raises(RedictumError, match="Unknown hotkey"):
            HotkeyListener._parse_key("bogus")

    def test_escape(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        assert HotkeyListener._parse_key("escape") == Key.esc
        assert HotkeyListener._parse_key("esc") == Key.esc

    def test_pause(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        assert HotkeyListener._parse_key("Pause") == Key.pause


class TestParseCombo:
    """HotkeyListener._parse_combo: "ctrl+Insert" → (key, mods)."""

    def test_ctrl_insert(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        key, mods = HotkeyListener._parse_combo("ctrl+Insert")
        assert key == Key.insert
        assert Key.ctrl_l in mods or Key.ctrl_r in mods

    def test_plain_key(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        key, mods = HotkeyListener._parse_combo("Insert")
        assert key == Key.insert
        assert len(mods) == 0

    def test_bad_modifier_raises(self):
        from redictum import HotkeyListener, RedictumError

        with pytest.raises(RedictumError, match="Unknown modifier"):
            HotkeyListener._parse_combo("badmod+X")

    def test_alt_f12(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener

        key, mods = HotkeyListener._parse_combo("alt+F12")
        assert key == Key.f12
        assert any(
            m in mods for m in (Key.alt_l, Key.alt_r, Key.alt_gr)
            if hasattr(Key, m.name)
        )
