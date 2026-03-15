# Feature: Store daemon PID in .state instead of separate PID file

## Status: REJECTED (2026-02-24)

**Причина:** текущая реализация с отдельным PID-файлом надёжнее.
Атомарность `O_EXCL` при создании PID-файла — проверенный Unix-паттерн.
Перенос в JSON `.state` теряет атомарность (read-modify-write) и создаёт
риски повреждения данных при крашах. Выигрыш (один файл вместо двух)
не оправдывает усложнение и потерю надёжности.

## Goal

Replace the separate `redictum.pid` file with a `"daemon_pid"` key in `.state`.
Consolidates runtime metadata into a single file.

## Current behavior

- `Daemon` class writes/reads `redictum.pid` (plain text, one PID number)
- PID file created with `O_EXCL` + `0o644` permissions (security fix from v1.2.1)
- Used by: `run_start()`, `run_stop()`, `run_status()`, double-start detection

## Changes needed

- `Daemon.__init__`: accept `state_mgr` instead of / alongside `pid_path`
- `_write_pid()` → `state_mgr.set("daemon_pid", pid)`
- `_read_pid()` → `state_mgr.get("daemon_pid")`
- `status()` / `stop()` / stale PID cleanup → use state_mgr
- Remove PID on daemon stop: `state_mgr.set("daemon_pid", None)`
- Remove `PID_FILENAME` constant and `self._pid_path` from `RedictumApp`
- Update `--config` cleanup (currently deletes `.state` — PID goes with it, correct)
- Update E2E: `cleanup_test` removes `redictum.pid` → no longer needed
- Update E2E: `read_pid`, `wait_for_pid_file`, assertions → read from `.state`

## Verification

- Thorough manual testing of daemon lifecycle:
  - `./redictum start` → PID in `.state`, process alive
  - `./redictum status` → shows running PID
  - `./redictum stop` → PID cleared from `.state`, process stopped
  - `./redictum start && ./redictum start` → double-start detection works
  - Kill daemon with `kill -9` → stale PID detected and cleaned on next start
- All 13 E2E tests pass
- All unit tests pass
- No leftover `redictum.pid` files created anywhere

## Risk

- Higher impact change — touches daemon lifecycle, PID atomicity, stale detection
- `O_EXCL` atomicity of PID file is lost (JSON read-modify-write is not atomic)
- Need to carefully handle: crash during write, concurrent access, race conditions
- Consider if atomic PID file was there for a reason and if `.state` is sufficient
