# Feature: Test coverage metrics, thread tests, and CI/CD

## Problem

1. **No coverage metrics** — 287 tests exist but we don't know what % of code they cover.
   Untested paths are invisible.

2. **No thread safety tests** — `_on_hold`, `_on_release`, `_run_pipeline`,
   `SoundNotifier._ensure_tones()` are all multi-threaded but have zero concurrency tests.

3. **No CI/CD** — tests only run locally. PRs and pushes are not gated.

4. **No linter in CI** — design.md mentions ruff, but no config exists.

## Changes needed

### 1. Add pytest-cov

```bash
pip install pytest-cov
pytest tests/ --cov=redictum --cov-report=term-missing --cov-report=html
```

Add to `pyproject.toml` (or `setup.cfg`):
```toml
[tool.pytest.ini_options]
addopts = "--cov=redictum --cov-report=term-missing --cov-fail-under=60"
```

Target: 60% initially, increase to 75%+ as gaps are filled.

### 2. Add thread safety tests

Priority tests to add:
- `SoundNotifier`: concurrent `_play()` calls → no crash, one temp dir
- `_on_hold` + `_on_release`: rapid fire → state transitions are correct
- `_run_pipeline`: verify state returns to IDLE on success and on error
- Graceful shutdown during recording → clean cancel
- Graceful shutdown during processing → waits for completion

### 3. Add untested code paths

Currently missing coverage for:
- `_main_loop` (complex, needs mock listener)
- `_graceful_shutdown`
- `_run_pipeline` (integration flow)
- `_generate_tones()` (can at least verify output format)
- `_language_wizard` (interactive input)
- `_log_system_info` (can verify it doesn't crash)
- `Daemon.start()` (double-fork is hard to test)

### 4. GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install pynput pytest pytest-cov
      - run: pytest tests/ --cov --cov-fail-under=60
  lint:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check redictum tests/
  e2e:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up --build --abort-on-container-exit
```

### 5. Ruff configuration

```toml
# ruff.toml
target-version = "py310"
line-length = 100

[lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]  # line length handled separately

[lint.per-file-ignores]
"tests/*" = ["S101"]  # assert in tests is fine
```

## Phasing

1. First: add ruff.toml + fix lint errors (quick win)
2. Then: add pytest-cov + identify gaps
3. Then: add thread safety tests for critical paths
4. Then: GitHub Actions CI
5. Then: increase coverage threshold

## Verification

- `ruff check redictum tests/` → 0 errors
- `pytest --cov --cov-fail-under=60` → pass
- GitHub Actions green on push
