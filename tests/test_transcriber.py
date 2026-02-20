"""Tests for Transcriber — the most critical test file.

Documents whisper translate mode behavior:
- translate=True → --translate, NO -l flag, NO --prompt
- translate=False → -l <lang>, --prompt "..."
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def make_transcriber(tmp_path):
    """Factory for Transcriber with configurable params."""

    def _make(language="ru", prompt="Test prompt.", timeout=120):
        from redictum import Transcriber

        # Create temporary files for whisper CLI and model
        cli_path = tmp_path / "whisper-cli"
        cli_path.touch()
        cli_path.chmod(0o755)
        
        model_path = tmp_path / "model.bin"
        model_path.write_bytes(b"fake model data")

        return Transcriber(
            whisper_cli=str(cli_path),
            model_path=str(model_path),
            language=language,
            prompt=prompt,
            timeout=timeout,
        )

    return _make


class TestCommandBuilding:
    """Verify the whisper-cli command line for various translate × language × prompt combos."""

    @pytest.mark.parametrize(
        "translate, language, prompt, must_have, must_not_have",
        [
            # Normal transcribe: has -l and --prompt
            (
                False,
                "ru",
                "Prompt text.",
                ["-l", "ru", "--prompt", "Prompt text."],
                ["--translate"],
            ),
            # Translate mode: --translate only, NO -l, NO --prompt
            (
                True,
                "ru",
                "Prompt text.",
                ["--translate"],
                ["-l", "--prompt"],
            ),
            # Transcribe with empty language: no -l flag
            (
                False,
                "",
                "Prompt text.",
                ["--prompt", "Prompt text."],
                ["-l", "--translate"],
            ),
            # Transcribe with no prompt: no --prompt flag
            (
                False,
                "en",
                "",
                ["-l", "en"],
                ["--prompt", "--translate"],
            ),
            # Translate with empty language and prompt (edge case)
            (
                True,
                "",
                "",
                ["--translate"],
                ["-l", "--prompt"],
            ),
        ],
        ids=[
            "transcribe-ru-with-prompt",
            "translate-ignores-lang-and-prompt",
            "transcribe-no-language",
            "transcribe-no-prompt",
            "translate-empty-everything",
        ],
    )
    def test_command_flags(
        self,
        translate,
        language,
        prompt,
        must_have,
        must_not_have,
        make_transcriber,
        monkeypatch,
    ):
        transcriber = make_transcriber(language=language, prompt=prompt)
        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Hello world"
            result.stderr = ""
            return result

        monkeypatch.setattr("subprocess.run", fake_run)
        transcriber.transcribe(Path("/tmp/test.wav"), translate=translate)

        for flag in must_have:
            assert flag in captured_cmd, f"Expected {flag!r} in {captured_cmd}"
        for flag in must_not_have:
            assert flag not in captured_cmd, f"Unexpected {flag!r} in {captured_cmd}"


class TestTranscribeResult:
    """Verify output handling: text, blank audio, errors."""

    def test_stdout_returned(self, make_transcriber, monkeypatch):
        transcriber = make_transcriber()

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "  Hello world  "
            r.stderr = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert transcriber.transcribe(Path("/tmp/t.wav")) == "Hello world"

    @pytest.mark.parametrize("blank", ["[BLANK_AUDIO]", "[ЗВУК]", "(silence)", "", "  "])
    def test_blank_audio_returns_empty(self, blank, make_transcriber, monkeypatch):
        transcriber = make_transcriber()

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = blank
            r.stderr = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        assert transcriber.transcribe(Path("/tmp/t.wav")) == ""

    def test_nonzero_returncode_raises(self, make_transcriber, monkeypatch):
        from redictum import RedictumError

        transcriber = make_transcriber()

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = ""
            r.stderr = "some error"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        with pytest.raises(RedictumError, match="whisper-cli failed"):
            transcriber.transcribe(Path("/tmp/t.wav"))

    def test_timeout_raises(self, make_transcriber, monkeypatch):
        import subprocess
        from redictum import RedictumError

        transcriber = make_transcriber(timeout=1)

        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 1)

        monkeypatch.setattr("subprocess.run", fake_run)
        with pytest.raises(RedictumError, match="timed out"):
            transcriber.transcribe(Path("/tmp/t.wav"))
