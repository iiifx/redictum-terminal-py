"""Tests for hotkey command: reassign push-to-talk keys."""

import pytest

# ---------------------------------------------------------------------------
# build_parser: hotkey subcommand
# ---------------------------------------------------------------------------

class TestBuildParserHotkey:
    """build_parser: 'hotkey' subcommand is registered."""

    def test_parse_hotkey(self):
        from redictum import build_parser
        parser = build_parser()
        args = parser.parse_args(["hotkey"])
        assert args.command == "hotkey"


# ---------------------------------------------------------------------------
# _parse_key: mouse button support
# ---------------------------------------------------------------------------

class TestParseKeyMouse:
    """HotkeyListener._parse_key: mouse button parsing."""

    def test_mouse_middle(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._parse_key("mouse_middle") == Button.middle

    def test_mouse_back(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._parse_key("mouse_back") == Button.button8

    def test_mouse_forward(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._parse_key("mouse_forward") == Button.button9

    def test_mouse_generic_button10(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._parse_key("mouse_button10") == Button.button10

    def test_mouse_case_insensitive(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._parse_key("Mouse_Back") == Button.button8

    def test_keyboard_still_works(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        assert HotkeyListener._parse_key("Insert") == Key.insert
        assert HotkeyListener._parse_key("F12") == Key.f12


# ---------------------------------------------------------------------------
# _parse_combo: mouse button in combo
# ---------------------------------------------------------------------------

class TestParseComboMouse:
    """HotkeyListener._parse_combo: mouse button with modifiers."""

    def test_plain_mouse_back(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        key, mods = HotkeyListener._parse_combo("mouse_back")
        assert key == Button.button8
        assert mods == frozenset()

    def test_ctrl_mouse_back(self):
        from pynput.keyboard import Key
        from pynput.mouse import Button
        from redictum import HotkeyListener
        key, mods = HotkeyListener._parse_combo("ctrl+mouse_back")
        assert key == Button.button8
        assert Key.ctrl_l in mods or Key.ctrl_r in mods


# ---------------------------------------------------------------------------
# _key_to_str: reverse conversion
# ---------------------------------------------------------------------------

class TestKeyToStr:
    """HotkeyListener._key_to_str: pynput objects back to config strings."""

    def test_keyboard_insert(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(Key.insert) == "Insert"

    def test_keyboard_f12(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(Key.f12) == "F12"

    def test_keyboard_escape(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        result = HotkeyListener._key_to_str(Key.esc)
        assert result.lower() in ("escape", "esc")

    def test_keyboard_char(self):
        from pynput.keyboard import KeyCode
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(KeyCode.from_char("a")) == "a"

    def test_mouse_middle(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(Button.middle) == "mouse_middle"

    def test_mouse_back(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(Button.button8) == "mouse_back"

    def test_mouse_forward(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(Button.button9) == "mouse_forward"

    def test_mouse_generic(self):
        from pynput.mouse import Button
        from redictum import HotkeyListener
        assert HotkeyListener._key_to_str(Button.button10) == "mouse_button10"

    def test_mouse_button8_normalizes_to_alias(self):
        """mouse_button8 is parsed same as mouse_back; _key_to_str returns alias."""
        from pynput.mouse import Button
        from redictum import HotkeyListener
        # Both parse to the same object
        assert HotkeyListener._parse_key("mouse_button8") == Button.button8
        assert HotkeyListener._parse_key("mouse_back") == Button.button8
        # _key_to_str prefers the named alias
        assert HotkeyListener._key_to_str(Button.button8) == "mouse_back"


# ---------------------------------------------------------------------------
# _combo_to_str: full combo conversion
# ---------------------------------------------------------------------------

class TestComboToStr:
    """HotkeyListener._combo_to_str: trigger + modifiers to string."""

    def test_plain_key(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        result = HotkeyListener._combo_to_str(Key.insert, frozenset())
        assert result == "Insert"

    def test_ctrl_key(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        result = HotkeyListener._combo_to_str(
            Key.insert, frozenset({Key.ctrl_l}),
        )
        assert result == "ctrl+Insert"

    def test_ctrl_mouse_back(self):
        from pynput.keyboard import Key
        from pynput.mouse import Button
        from redictum import HotkeyListener
        result = HotkeyListener._combo_to_str(
            Button.button8, frozenset({Key.ctrl_l}),
        )
        assert result == "ctrl+mouse_back"

    def test_shift_alt(self):
        from pynput.keyboard import Key
        from redictum import HotkeyListener
        result = HotkeyListener._combo_to_str(
            Key.f1, frozenset({Key.shift_l, Key.alt_l}),
        )
        # Both modifiers present, order: ctrl, alt, shift
        assert "alt" in result
        assert "shift" in result
        assert "F1" in result


# ---------------------------------------------------------------------------
# Round-trip: parse → to_str → parse
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Parse → _key_to_str → _parse_key: round-trip consistency."""

    @pytest.mark.parametrize("combo", [
        "Insert", "F12", "ctrl+Insert", "ctrl+F1",
        "mouse_back", "mouse_forward", "mouse_middle",
        "ctrl+mouse_back", "shift+mouse_forward",
    ])
    def test_round_trip(self, combo):
        from redictum import HotkeyListener
        key, mods = HotkeyListener._parse_combo(combo)
        result = HotkeyListener._combo_to_str(key, mods)
        # Re-parse the result
        key2, mods2 = HotkeyListener._parse_combo(result)
        assert key == key2
        # Modifier groups should match (same group membership)
        assert HotkeyListener._combo_to_str(key2, mods2) == result


# ---------------------------------------------------------------------------
# run_hotkey: scenarios
# ---------------------------------------------------------------------------

class TestRunHotkey:
    """RedictumApp.run_hotkey: interactive hotkey change flow."""

    @pytest.fixture()
    def app(self, tmp_path):
        from redictum import RedictumApp
        return RedictumApp(tmp_path)

    def test_quiet_mode_rejects(self, app, monkeypatch):
        import redictum
        from redictum import EXIT_ERROR
        monkeypatch.setattr(redictum, "_verbosity", -1)
        assert app.run_hotkey() == EXIT_ERROR

    def test_cancel_on_empty_input(self, app, monkeypatch):
        from redictum import EXIT_OK
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert app.run_hotkey() == EXIT_OK

    def test_cancel_on_eof(self, app, monkeypatch):
        from redictum import EXIT_OK
        def raise_eof(_):
            raise EOFError
        monkeypatch.setattr("builtins.input", raise_eof)
        assert app.run_hotkey() == EXIT_OK

    def test_cancel_on_keyboard_interrupt_at_prompt(self, app, monkeypatch):
        from redictum import EXIT_OK
        def raise_ki(_):
            raise KeyboardInterrupt
        monkeypatch.setattr("builtins.input", raise_ki)
        assert app.run_hotkey() == EXIT_OK

    def test_unsupported_key_rejected(self, app, monkeypatch):
        import redictum
        from pynput.keyboard import Key
        from redictum import EXIT_ERROR

        monkeypatch.setattr("builtins.input", lambda _: "1")
        # Arrow keys are not in _KEY_MAP — should be rejected
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Key.up, frozenset()),
        )
        assert app.run_hotkey() == EXIT_ERROR

    def test_conflict_rejected(self, app, monkeypatch):
        import redictum
        from pynput.keyboard import Key
        from redictum import EXIT_ERROR

        monkeypatch.setattr("builtins.input", lambda _: "1")
        # Capture returns the same key as translate (ctrl+Insert)
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Key.insert, frozenset({Key.ctrl_l, Key.ctrl_r})),
        )
        assert app.run_hotkey() == EXIT_ERROR

    def test_save_record_hotkey(self, app, monkeypatch, tmp_path):
        import redictum
        from pynput.keyboard import Key
        from redictum import EXIT_OK

        monkeypatch.setattr("builtins.input", lambda _: "1")
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Key.f12, frozenset()),
        )
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)

        assert app.run_hotkey() == EXIT_OK

        # Verify config was updated
        config_text = (tmp_path / "config.ini").read_text()
        assert "F12" in config_text

    def test_save_translate_hotkey(self, app, monkeypatch, tmp_path):
        import redictum
        from pynput.keyboard import Key
        from redictum import EXIT_OK

        monkeypatch.setattr("builtins.input", lambda _: "2")
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Key.f5, frozenset({Key.ctrl_l, Key.ctrl_r})),
        )
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)

        assert app.run_hotkey() == EXIT_OK

        config_text = (tmp_path / "config.ini").read_text()
        assert "ctrl+F5" in config_text

    def test_save_mouse_hotkey(self, app, monkeypatch, tmp_path):
        import redictum
        from pynput.mouse import Button
        from redictum import EXIT_OK

        monkeypatch.setattr("builtins.input", lambda _: "1")
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Button.button8, frozenset()),
        )
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)

        assert app.run_hotkey() == EXIT_OK

        config_text = (tmp_path / "config.ini").read_text()
        assert "mouse_back" in config_text

    def test_user_declines_save(self, app, monkeypatch):
        import redictum
        from pynput.keyboard import Key
        from redictum import EXIT_OK

        monkeypatch.setattr("builtins.input", lambda _: "1")
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Key.f12, frozenset()),
        )
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)

        assert app.run_hotkey() == EXIT_OK

    def test_daemon_notice(self, app, monkeypatch, capsys):
        import redictum
        from pynput.keyboard import Key
        from redictum import Daemon

        monkeypatch.setattr("builtins.input", lambda _: "1")
        monkeypatch.setattr(
            redictum, "_capture_hotkey",
            lambda: (Key.f12, frozenset()),
        )
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)
        monkeypatch.setattr(Daemon, "status", lambda self: 12345)

        app.run_hotkey()
        captured = capsys.readouterr().out
        assert "Daemon is running" in captured
