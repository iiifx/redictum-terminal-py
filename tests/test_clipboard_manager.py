"""Tests for ClipboardManager, ClipboardBackend ABC, and XclipBackend."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def clipboard():
    from redictum import ClipboardManager, XclipBackend

    return ClipboardManager(XclipBackend())


# ── ClipboardBackend ABC ─────────────────────────────────────────────


class TestClipboardBackendABC:
    """ClipboardBackend cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        from redictum import ClipboardBackend

        with pytest.raises(TypeError):
            ClipboardBackend()  # type: ignore[abstract]

    def test_subclass_must_implement_all(self):
        from redictum import ClipboardBackend

        class Incomplete(ClipboardBackend):
            def copy(self, text):
                pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


# ── XclipBackend unit tests ──────────────────────────────────────────


class TestXclipBackend:
    """XclipBackend: xclip/xdotool subprocess management."""

    def test_copy_calls_xclip(self, monkeypatch):
        from redictum import XclipBackend

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", fake_run)
        backend = XclipBackend()
        backend.copy("hello")
        assert len(calls) == 1
        assert "xclip" in calls[0][0]
        assert calls[0][1]["input"] == b"hello"

    def test_paste_calls_xdotool(self, monkeypatch):
        from redictum import XclipBackend

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr("time.sleep", lambda _: None)
        backend = XclipBackend()
        backend.paste()
        assert len(calls) == 1
        assert "xdotool" in calls[0]

    def test_get_targets_returns_list(self, monkeypatch):
        from redictum import XclipBackend

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "TARGETS\ntext/plain\nimage/png\n"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        backend = XclipBackend()
        targets = backend.get_targets()
        assert targets == ["TARGETS", "text/plain", "image/png"]

    def test_get_targets_empty_on_failure(self, monkeypatch):
        from redictum import XclipBackend

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        backend = XclipBackend()
        assert backend.get_targets() == []

    def test_save_target_returns_bytes(self, monkeypatch):
        from redictum import XclipBackend

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = b"raw data"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        backend = XclipBackend()
        assert backend.save_target("text/plain") == b"raw data"

    def test_save_target_returns_none_on_failure(self, monkeypatch):
        from redictum import XclipBackend

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = b""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        backend = XclipBackend()
        assert backend.save_target("text/plain") is None

    def test_restore_target_calls_xclip(self, monkeypatch):
        from redictum import XclipBackend

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return MagicMock(returncode=0)

        monkeypatch.setattr("subprocess.run", fake_run)
        backend = XclipBackend()
        backend.restore_target("text/plain", b"data")
        assert len(calls) == 1
        assert "text/plain" in calls[0][0]
        assert calls[0][1]["input"] == b"data"


# ── ClipboardManager integration tests (via XclipBackend) ───────────


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
                # get_targets call
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
