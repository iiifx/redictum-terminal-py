"""Shared fixtures for Redictum Terminal tests.

Loads the ``redictum`` module (no .py extension) via importlib so that
all test files can do ``from redictum import ...``.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module loader — register ``redictum`` in sys.modules
# ---------------------------------------------------------------------------

_MODULE_PATH = Path(__file__).resolve().parent.parent / "redictum"


@pytest.fixture(scope="session", autouse=True)
def _load_redictum_module():
    """Load the ``redictum`` script as a Python module (session-scoped)."""
    if "redictum" not in sys.modules:
        loader = importlib.machinery.SourceFileLoader("redictum", str(_MODULE_PATH))
        spec = importlib.util.spec_from_file_location(
            "redictum", str(_MODULE_PATH), loader=loader,
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["redictum"] = mod
        spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def default_config():
    """Return a deep copy of DEFAULT_CONFIG for safe mutation in tests."""
    from redictum import DEFAULT_CONFIG, ConfigManager
    return ConfigManager._deep_copy(DEFAULT_CONFIG)


@pytest.fixture()
def config_dir(tmp_path):
    """Return a tmp directory with a freshly created ConfigManager."""
    from redictum import ConfigManager
    mgr = ConfigManager(tmp_path)
    return tmp_path, mgr


@pytest.fixture()
def mock_subprocess(monkeypatch):
    """Provide a pre-configured MagicMock for subprocess.run."""
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    monkeypatch.setattr("subprocess.run", mock)
    return mock
