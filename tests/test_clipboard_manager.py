"""Tests for ClipboardManager."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest


@pytest.fixture()
def clipboard():
    from redictum import ClipboardManager

    return ClipboardManager()


class TestDetectTarget:
    """ClipboardManager._detect_target: parse TARGETS from xclip."""

    def test_text_plain(self, clipboard, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "TARGETS\nMULTIPLE\ntext/plain\nTIMESTAMP\n"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert clipboard._detect_target() == "text/plain"

    def test_image_png(self, clipboard, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "TARGETS\nimage/png\ntext/html\n"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert clipboard._detect_target() == "image/png"

    def test_only_skip_targets(self, clipboard, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "TARGETS\nMULTIPLE\nTIMESTAMP\n"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert clipboard._detect_target() is None

    def test_xclip_error(self, clipboard, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert clipboard._detect_target() is None


class TestCopy:
    """ClipboardManager.copy: sends text as bytes to xclip."""

    def test_copy_sends_bytes(self, clipboard, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", fake_run)
        clipboard.copy("hello")
        assert len(calls) == 1
        assert calls[0][1]["input"] == b"hello"
        assert "clipboard" in calls[0][0]


class TestPaste:
    """ClipboardManager.paste: xdotool ctrl+v."""

    def test_paste_calls_xdotool(self, clipboard, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr("time.sleep", lambda _: None)
        clipboard.paste()
        assert len(calls) == 1
        assert "xdotool" in calls[0]
        assert "ctrl+v" in calls[0]


class TestSaveRestore:
    """ClipboardManager.save/restore: round-trip."""

    def test_save_returns_target_and_data(self, clipboard, monkeypatch):
        call_count = [0]

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            call_count[0] += 1
            if call_count[0] == 1:
                # _detect_target call
                r.stdout = "TARGETS\ntext/plain\n"
            else:
                # actual save call
                r.stdout = b"saved data"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        result = clipboard.save()
        assert result is not None
        assert result[0] == "text/plain"
        assert result[1] == b"saved data"

    def test_save_empty_clipboard(self, clipboard, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert clipboard.save() is None

    def test_restore_calls_xclip(self, clipboard, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", fake_run)
        clipboard.restore(("text/plain", b"some data"))
        assert len(calls) == 1
        assert "text/plain" in calls[0][0]
        assert calls[0][1]["input"] == b"some data"
