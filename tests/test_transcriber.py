"""Tests for Transcriber — the most critical test file.

Documents whisper translate mode behavior:
- translate=True → --translate, NO -l flag, NO --prompt
- translate=False → -l <lang>, --prompt "..."

Documents language-prompt resolution:
- "auto" + known language → auto-select from LANGUAGE_PROMPTS
- "auto" + unknown language → no prompt
- Non-empty user prompt → override (use as-is)
- Empty user prompt → no prompt (disabled)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def make_transcriber(tmp_path):
    """Factory for Transcriber with configurable params."""

    cli = tmp_path / "whisper-cli"
    cli.touch(mode=0o755)
    model = tmp_path / "model.bin"
    model.touch()

    def _make(language="ru", prompt="auto", timeout=120):
        from redictum import Transcriber

        return Transcriber(
            whisper_cli=str(cli),
            model_path=str(model),
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
            # Normal transcribe with explicit prompt: has -l and --prompt
            (
                False,
                "ru",
                "Custom prompt.",
                ["-l", "ru", "--prompt", "Custom prompt."],
                ["--translate"],
            ),
            # Translate mode: --translate only, NO -l, NO --prompt
            (
                True,
                "ru",
                "Custom prompt.",
                ["--translate"],
                ["-l", "--prompt"],
            ),
            # Transcribe with empty language and custom prompt
            (
                False,
                "",
                "Custom prompt.",
                ["--prompt", "Custom prompt."],
                ["-l", "--translate"],
            ),
            # Auto prompt with known language: selects from LANGUAGE_PROMPTS
            (
                False,
                "en",
                "auto",
                ["-l", "en", "--prompt"],
                ["--translate"],
            ),
            # Auto prompt with unknown language: no --prompt
            (
                False,
                "xx",
                "auto",
                ["-l", "xx"],
                ["--prompt", "--translate"],
            ),
            # Empty prompt (disabled): no --prompt even for known language
            (
                False,
                "ru",
                "",
                ["-l", "ru"],
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
            "transcribe-ru-custom-prompt",
            "translate-ignores-lang-and-prompt",
            "transcribe-no-language-custom-prompt",
            "transcribe-en-auto-prompt",
            "transcribe-unknown-lang-auto-no-prompt",
            "transcribe-ru-prompt-disabled",
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


class TestResolvePrompt:
    """Verify _resolve_prompt logic: auto vs override vs disabled."""

    def test_auto_known_language(self, make_transcriber):
        """'auto' + known language → select from LANGUAGE_PROMPTS."""
        from redictum import LANGUAGE_PROMPTS

        transcriber = make_transcriber(language="ru", prompt="auto")
        assert transcriber._resolve_prompt() == LANGUAGE_PROMPTS["ru"]

    def test_auto_unknown_language(self, make_transcriber):
        """'auto' + unknown language → None (no prompt)."""
        transcriber = make_transcriber(language="xx", prompt="auto")
        assert transcriber._resolve_prompt() is None

    def test_auto_all_languages(self, make_transcriber):
        """Every language in LANGUAGE_PROMPTS is resolvable via 'auto'."""
        from redictum import LANGUAGE_PROMPTS

        for lang in LANGUAGE_PROMPTS:
            transcriber = make_transcriber(language=lang, prompt="auto")
            result = transcriber._resolve_prompt()
            assert result == LANGUAGE_PROMPTS[lang], f"Failed for language: {lang}"

    def test_custom_prompt_overrides(self, make_transcriber):
        """Non-empty custom prompt takes priority over LANGUAGE_PROMPTS."""
        transcriber = make_transcriber(language="ru", prompt="My custom prompt.")
        assert transcriber._resolve_prompt() == "My custom prompt."

    def test_empty_prompt_disabled(self, make_transcriber):
        """Empty string → no prompt (disabled)."""
        transcriber = make_transcriber(language="ru", prompt="")
        assert transcriber._resolve_prompt() is None


class TestAutoPromptE2E:
    """End-to-end: verify auto-prompt reaches whisper command for every language."""

    @pytest.mark.parametrize("lang", [
        "en", "zh", "hi", "es", "ar", "fr", "pt",
        "ru", "de", "ja", "uk", "ko", "it", "tr", "pl",
    ])
    def test_auto_prompt_in_command(self, lang, make_transcriber, monkeypatch):
        """prompt='auto' + language → correct LANGUAGE_PROMPTS[lang] in whisper cmd."""
        from redictum import LANGUAGE_PROMPTS

        transcriber = make_transcriber(language=lang, prompt="auto")
        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "text"
            r.stderr = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        transcriber.transcribe(Path("/tmp/test.wav"))

        assert "--prompt" in captured_cmd, f"--prompt missing for {lang}"
        idx = captured_cmd.index("--prompt")
        assert captured_cmd[idx + 1] == LANGUAGE_PROMPTS[lang], (
            f"Wrong prompt for {lang}"
        )


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
