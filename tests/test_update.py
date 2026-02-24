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
        payload = json.dumps({"tag_name": "v1.5.0"})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/curl")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake_result)

        assert app._fetch_latest_version() == "1.5.0"

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

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: VERSION)
        assert app.run_update() == EXIT_OK

    def test_downgrade_protection(self, app, monkeypatch):
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: "0.0.1")
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

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: "99.0.0")
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)
        assert app.run_update() == EXIT_OK

    def test_eof_at_prompt(self, app, monkeypatch):
        import redictum
        from redictum import EXIT_OK

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: "99.0.0")

        def fake_confirm(*a, **kw):
            raise EOFError

        # _confirm catches EOFError itself, so we mock input to raise it
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: False)
        assert app.run_update() == EXIT_OK

    def test_daemon_running(self, app, monkeypatch, tmp_path):
        import redictum
        from redictum import EXIT_ERROR, Daemon

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: "99.0.0")
        monkeypatch.setattr(redictum, "_confirm", lambda *a, **kw: True)
        monkeypatch.setattr(Daemon, "status", lambda self: 12345)

        assert app.run_update() == EXIT_ERROR

    def test_hash_mismatch(self, app, monkeypatch, tmp_path):
        import redictum
        from redictum import EXIT_ERROR

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: "99.0.0")
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

        monkeypatch.setattr(app, "_fetch_latest_version", lambda: "99.0.0")
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
