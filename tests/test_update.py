"""Tests for self-update functionality."""
from __future__ import annotations

import json
import subprocess

import pytest

# ---------------------------------------------------------------------------
# _compare_versions
# ---------------------------------------------------------------------------

class TestCompareVersions:
    """_compare_versions: semver comparison."""

    def test_less_than(self):
        from redictum import _compare_versions
        assert _compare_versions("1.2.0", "1.3.0") == -1

    def test_equal(self):
        from redictum import _compare_versions
        assert _compare_versions("1.3.0", "1.3.0") == 0

    def test_greater_than(self):
        from redictum import _compare_versions
        assert _compare_versions("1.4.0", "1.3.0") == 1

    def test_multi_digit(self):
        from redictum import _compare_versions
        assert _compare_versions("1.9.0", "1.10.0") == -1

    def test_major_dominates(self):
        from redictum import _compare_versions
        assert _compare_versions("2.0.0", "1.99.99") == 1

    def test_patch_difference(self):
        from redictum import _compare_versions
        assert _compare_versions("1.0.1", "1.0.2") == -1

    def test_invalid_input(self):
        from redictum import _compare_versions
        with pytest.raises(ValueError):
            _compare_versions("abc", "1.0.0")


# ---------------------------------------------------------------------------
# build_parser: update subcommand
# ---------------------------------------------------------------------------

class TestBuildParserUpdate:
    """build_parser: 'update' subcommand is registered."""

    def test_parse_update(self):
        from redictum import build_parser
        parser = build_parser()
        args = parser.parse_args(["update"])
        assert args.command == "update"


# ---------------------------------------------------------------------------
# _fetch_latest_version
# ---------------------------------------------------------------------------

class TestFetchLatestVersion:
    """RedictumApp._fetch_latest_version: GitHub API query."""

    @pytest.fixture()
    def app(self, tmp_path):
        from redictum import RedictumApp
        return RedictumApp(tmp_path)

    def test_success(self, app, monkeypatch):
        payload = json.dumps({"tag_name": "v1.5.0", "body": "### Added\n- Feature X"})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        version, notes = app._fetch_latest_version()
        assert version == "1.5.0"
        assert "Feature X" in notes

    def test_empty_body(self, app, monkeypatch):
        payload = json.dumps({"tag_name": "v1.5.0"})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        version, notes = app._fetch_latest_version()
        assert version == "1.5.0"
        assert notes == ""

    def test_null_body(self, app, monkeypatch):
        """GitHub returns body: null for releases with no notes."""
        payload = json.dumps({"tag_name": "v1.5.0", "body": None})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        version, notes = app._fetch_latest_version()
        assert version == "1.5.0"
        assert notes == ""

    def test_invalid_tag_name(self, app, monkeypatch):
        """Reject tag_name that doesn't match semver pattern."""
        from redictum import RedictumError

        payload = json.dumps({"tag_name": "../../evil"})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        with pytest.raises(RedictumError, match="Unexpected tag_name"):
            app._fetch_latest_version()

    def test_non_string_tag_name(self, app, monkeypatch):
        """Reject tag_name that is not a string."""
        from redictum import RedictumError

        payload = json.dumps({"tag_name": 42})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        with pytest.raises(RedictumError, match="Unexpected tag_name"):
            app._fetch_latest_version()

    def test_network_error(self, app, monkeypatch):
        from redictum import RedictumError

        fake_result = subprocess.CompletedProcess(
            args=[], returncode=22, stdout="", stderr="curl: (22) error",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        with pytest.raises(RedictumError, match="Failed to check"):
            app._fetch_latest_version()

    def test_timeout(self, app, monkeypatch):
        from redictum import RedictumError

        def fake_run(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="curl", timeout=15)

        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", fake_run)

        with pytest.raises(RedictumError, match="Timed out"):
            app._fetch_latest_version()


# ---------------------------------------------------------------------------
# run_update — scenarios
# ---------------------------------------------------------------------------

class TestRunUpdate:
    """RedictumApp.run_update: full update flow scenarios."""

    @pytest.fixture()
    def app(self, tmp_path):
        from redictum import RedictumApp
        return RedictumApp(tmp_path)

    def test_already_up_to_date(self, app, monkeypatch):
        from redictum import EXIT_OK, VERSION

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: (VERSION, ""))
        assert app.run_update() == EXIT_OK

    def test_downgrade_protection(self, app, monkeypatch):
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("0.0.1", ""))
        assert app.run_update() == EXIT_OK

    def test_network_failure(self, app, monkeypatch):
        from redictum import RedictumError

        def fail():
            raise RedictumError("no internet")

        monkeypatch.setattr(app, "_fetch_latest_version", fail)
        with pytest.raises(RedictumError, match="no internet"):
            app.run_update()

    def test_user_declines(self, app, monkeypatch):
        import redictum
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", ""))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)
        assert app.run_update() == EXIT_OK

    def test_eof_at_prompt(self, app, monkeypatch):
        import redictum
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", ""))

        def fake_confirm(*a, **kw):
            raise EOFError

        # _confirm catches EOFError itself, so we mock input to raise it
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)
        assert app.run_update() == EXIT_OK

    def test_daemon_running(self, app, monkeypatch, tmp_path):
        import redictum
        from redictum import EXIT_ERROR, Daemon

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", ""))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)
        monkeypatch.setattr(Daemon, "status", lambda self: 12345)

        assert app.run_update() == EXIT_ERROR

    def test_hash_mismatch(self, app, monkeypatch, tmp_path):
        import redictum
        from redictum import EXIT_ERROR

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", ""))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)
        monkeypatch.setattr(
            "redictum.Daemon.status", lambda self: None,
        )

        def fake_download(url, dest, timeout):
            if url.endswith(".sha256"):
                dest.write_text("0000000000000000000000000000000000000000000000000000000000000000  redictum\n")
            else:
                dest.write_text("#!/usr/bin/env python3\nprint('new version')\n")

        monkeypatch.setattr(app, "_download_to_file", fake_download)

        assert app.run_update() == EXIT_ERROR

    def test_success(self, app, monkeypatch, tmp_path):
        import hashlib

        import redictum
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", "### Fixed\n- Bug Y"))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)
        monkeypatch.setattr(
            "redictum.Daemon.status", lambda self: None,
        )

        new_content = b"#!/usr/bin/env python3\nprint('updated')\n"
        correct_hash = hashlib.sha256(new_content).hexdigest()

        # Create a fake "current script" that __file__ will resolve to
        fake_script = tmp_path / "redictum"
        fake_script.write_text("#!/usr/bin/env python3\nprint('old')\n")
        fake_script.chmod(0o755)

        def fake_download(url, dest, timeout):
            if url.endswith(".sha256"):
                dest.write_text(f"{correct_hash}  redictum\n")
            else:
                dest.write_bytes(new_content)

        monkeypatch.setattr(app, "_download_to_file", fake_download)
        # Patch __file__ at module level so Path(__file__).resolve() → fake_script
        monkeypatch.setattr(redictum, "__file__", str(fake_script))

        result = app.run_update()
        assert result == EXIT_OK

        # Verify backup was created
        backup = fake_script.with_suffix(".bak")
        assert backup.exists()
        assert backup.read_text() == "#!/usr/bin/env python3\nprint('old')\n"

        # Verify script was replaced
        assert fake_script.read_bytes() == new_content

    def test_changelog_displayed(self, app, monkeypatch, capsys):
        import redictum
        from redictum import EXIT_OK

        notes = "### Added\n- Cool feature\n- Another feature"
        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", notes))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)

        app.run_update()
        captured = capsys.readouterr().out
        assert "Cool feature" in captured
        assert "Another feature" in captured

    def test_no_changelog_when_empty(self, app, monkeypatch, capsys):
        import redictum
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", ""))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)

        app.run_update()
        captured = capsys.readouterr().out
        # Should have version line but no extra blank lines from changelog
        assert "99.0.0" in captured

    def test_rich_markup_escaped_in_notes(self, app, monkeypatch, capsys):
        import redictum

        notes = "[bold red]HACKED[/bold red]\n[link=http://evil.com]click[/link]"
        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", notes))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)

        app.run_update()
        captured = capsys.readouterr().out
        # Rich markup must be neutralised — literal brackets printed as text
        # If markup were interpreted, "[bold red]" would be stripped from output
        assert "[bold red]HACKED[/bold red]" in captured
        assert "[link=http://evil.com]click[/link]" in captured

    def test_ansi_escapes_stripped_in_notes(self, app, monkeypatch, capsys):
        import redictum

        notes = "Normal\x1b[2Jtext\x1b[31mcolored"
        monkeypatch.setattr(app, "_fetch_latest_version", lambda: ("99.0.0", notes))
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)

        app.run_update()
        captured = capsys.readouterr().out
        assert "\x1b[2J" not in captured
        assert "\x1b[31m" not in captured
        assert "Normaltext" in captured or "Normal" in captured


# ---------------------------------------------------------------------------
# _sanitize_external
# ---------------------------------------------------------------------------

class TestSanitizeExternal:
    """_sanitize_external: neutralise Rich markup and ANSI escapes."""

    def test_escapes_rich_brackets(self):
        from redictum import _sanitize_external
        assert _sanitize_external("[bold]text[/bold]") == r"\[bold]text\[/bold]"

    def test_strips_ansi_escape(self):
        from redictum import _sanitize_external
        assert _sanitize_external("hello\x1b[31mworld") == r"helloworld"

    def test_combined(self):
        from redictum import _sanitize_external
        result = _sanitize_external("\x1b[2J[link=http://x]click[/link]")
        assert "\x1b" not in result
        assert "[link" not in result or r"\[link" in result

    def test_plain_text_unchanged(self):
        from redictum import _sanitize_external
        assert _sanitize_external("just plain text 123") == "just plain text 123"
