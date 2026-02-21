#!/bin/bash
# =============================================================================
# Redictum Terminal — E2E Test Suite (Docker)
# =============================================================================
# Runs 10 daemon lifecycle tests in a clean Docker container.
# Usage: docker compose up --build --abort-on-container-exit
# =============================================================================

set -u

# -- Colors -------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

# -- Counters -----------------------------------------------------------------

PASS=0
FAIL=0

# -- Paths --------------------------------------------------------------------

WORKDIR="/opt/redictum-test"
SCRIPT="$WORKDIR/redictum"

# =============================================================================
# Assert helpers
# =============================================================================

assert_file_exists() {
    if [[ -f "$1" ]]; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: file not found: $1"
    return 1
}

assert_file_missing() {
    if [[ ! -f "$1" ]]; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: file should not exist: $1"
    return 1
}

assert_dir_exists() {
    if [[ -d "$1" ]]; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: directory not found: $1"
    return 1
}

assert_contains() {
    local text="$1"
    local pattern="$2"
    if echo "$text" | grep -qi "$pattern"; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: expected '$pattern' in output"
    echo -e "  Got: $text"
    return 1
}

assert_exit_ok() {
    if [[ $1 -eq 0 ]]; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: expected exit 0, got $1"
    return 1
}

assert_exit_error() {
    if [[ $1 -ne 0 ]]; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: expected non-zero exit, got 0"
    return 1
}

assert_pid_alive() {
    if kill -0 "$1" 2>/dev/null; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: PID $1 is not alive"
    return 1
}

assert_pid_dead() {
    if ! kill -0 "$1" 2>/dev/null; then
        return 0
    fi
    echo -e "  ${RED}FAIL${NC}: PID $1 is still alive"
    return 1
}

# =============================================================================
# Utility helpers
# =============================================================================

read_pid() {
    cat "$WORKDIR/redictum.pid" 2>/dev/null | tr -d '[:space:]'
}

wait_for_pid_file() {
    local i=0
    while [[ ! -f "$WORKDIR/redictum.pid" ]]; do
        sleep 0.2
        ((i++))
        if [[ $i -ge 25 ]]; then
            echo -e "  ${RED}FAIL${NC}: PID file not created within 5s"
            return 1
        fi
    done
    return 0
}

wait_for_pid_gone() {
    local pid=$1
    local max=${2:-25}
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 0.2
        ((i++))
        if [[ $i -ge $max ]]; then
            echo -e "  ${RED}FAIL${NC}: PID $pid still alive after timeout"
            return 1
        fi
    done
    return 0
}

# Wait for PID file + verify daemon is alive after settling
wait_for_daemon() {
    wait_for_pid_file || return 1
    sleep 0.5
    local pid
    pid=$(read_pid)
    if [[ -z "$pid" ]]; then
        echo -e "  ${RED}FAIL${NC}: PID file is empty"
        return 1
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
        echo -e "  ${RED}FAIL${NC}: daemon (PID $pid) died shortly after start"
        local latest_log
        latest_log=$(ls -t "$WORKDIR/logs/"*.log 2>/dev/null | head -1)
        if [[ -n "$latest_log" ]]; then
            echo "  Last log lines:"
            tail -5 "$latest_log" 2>/dev/null | sed 's/^/    /'
        fi
        return 1
    fi
    return 0
}

# After init(), config.yaml has default ~/whisper.cpp/... paths that don't
# exist.  Sed them to our fakes so _deps_ok() returns True on next start.
fix_whisper_config() {
    sed -i 's|cli:.*|cli: "/usr/local/bin/whisper-cli"|' "$WORKDIR/config.yaml"
    touch "$WORKDIR/fake-model.bin"
    sed -i 's|model:.*|model: "'$WORKDIR'/fake-model.bin"|' "$WORKDIR/config.yaml"
}

cleanup_test() {
    # Kill any running daemon
    if [[ -f "$WORKDIR/redictum.pid" ]]; then
        local pid
        pid=$(read_pid)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            local i=0
            while kill -0 "$pid" 2>/dev/null && [[ $i -lt 15 ]]; do
                sleep 0.2
                ((i++))
            done
        fi
    fi
    rm -f "$WORKDIR/config.yaml" "$WORKDIR/.initialized" "$WORKDIR/redictum.pid"
    rm -f "$WORKDIR/fake-model.bin"
    rm -rf "$WORKDIR/audio" "$WORKDIR/transcripts" "$WORKDIR/logs"
}

run_test() {
    local name="$1"
    local func="$2"
    cleanup_test 2>/dev/null
    echo -e "\n${BOLD}[$name]${NC}"
    if $func; then
        echo -e "  ${GREEN}PASS${NC}"
        ((PASS++))
    else
        echo -e "  ${RED}FAIL${NC}"
        ((FAIL++))
    fi
}

# =============================================================================
# Test cases
# =============================================================================

# T01: Clean first run — start creates config, marker, and directories
test_01_clean_first_run() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1
    fix_whisper_config

    assert_file_exists "$WORKDIR/config.yaml" || return 1
    assert_file_exists "$WORKDIR/.initialized" || return 1
    assert_dir_exists "$WORKDIR/audio" || return 1
    assert_dir_exists "$WORKDIR/transcripts" || return 1
    assert_dir_exists "$WORKDIR/logs" || return 1
}

# T02: Daemon starts — PID file exists and process is alive
test_02_daemon_starts() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1
    fix_whisper_config

    assert_file_exists "$WORKDIR/redictum.pid" || return 1
    local pid
    pid=$(read_pid)
    assert_pid_alive "$pid" || return 1
}

# T03: Status shows running + PID
test_03_status_running() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    fix_whisper_config
    local pid
    pid=$(read_pid)

    local output
    output=$(python3 "$SCRIPT" status 2>&1)
    assert_contains "$output" "running" || return 1
    assert_contains "$output" "$pid" || return 1
}

# T04: Double start — second start fails with "already running"
test_04_double_start() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    fix_whisper_config

    local output
    output=$(python3 "$SCRIPT" start </dev/null 2>&1)
    local rc=$?
    assert_exit_error $rc || return 1
    assert_contains "$output" "already running" || return 1
}

# T05: Stop daemon — PID file removed, process dead
test_05_stop_daemon() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    fix_whisper_config
    local pid
    pid=$(read_pid)

    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_pid_gone "$pid" || return 1
    assert_file_missing "$WORKDIR/redictum.pid" || return 1
    assert_pid_dead "$pid" || return 1
}

# T06: Status when not running
test_06_status_not_running() {
    local output
    output=$(python3 "$SCRIPT" status 2>&1)
    assert_contains "$output" "not running" || return 1
}

# T07: Stale PID file — start cleans it up and launches normally
test_07_stale_pid() {
    echo "99999" > "$WORKDIR/redictum.pid"

    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1
    fix_whisper_config

    local pid
    pid=$(read_pid)
    if [[ "$pid" == "99999" ]]; then
        echo -e "  ${RED}FAIL${NC}: PID should not be 99999 (stale not cleaned)"
        return 1
    fi
    assert_pid_alive "$pid" || return 1
}

# T08: --config resets config.yaml (fresh mtime)
test_08_config_reset() {
    # First start to create initial files
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    fix_whisper_config
    local pid
    pid=$(read_pid)

    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    wait_for_pid_gone "$pid" || return 1

    local old_mtime
    old_mtime=$(stat -c %Y "$WORKDIR/config.yaml")
    sleep 1.1  # ensure different mtime (1-second resolution)

    # --config deletes config.yaml + .initialized, then start recreates them
    python3 "$SCRIPT" --config start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1
    fix_whisper_config

    local new_mtime
    new_mtime=$(stat -c %Y "$WORKDIR/config.yaml")
    if [[ "$new_mtime" -le "$old_mtime" ]]; then
        echo -e "  ${RED}FAIL${NC}: config.yaml not recreated (mtime unchanged)"
        return 1
    fi
}

# T09: Restart cycle — stop then start, PID alive
test_09_restart_cycle() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    fix_whisper_config
    local pid1
    pid1=$(read_pid)

    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    wait_for_pid_gone "$pid1" || return 1

    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1

    local pid2
    pid2=$(read_pid)
    assert_pid_alive "$pid2" || return 1
}

# T10: SIGTERM graceful shutdown — process exits, PID file cleaned by atexit
test_10_sigterm_graceful() {
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    fix_whisper_config
    local pid
    pid=$(read_pid)

    kill -TERM "$pid"
    wait_for_pid_gone "$pid" || return 1
    sleep 0.5  # let atexit cleanup run
    assert_file_missing "$WORKDIR/redictum.pid" || return 1
}

# =============================================================================
# Main
# =============================================================================

echo -e "${BOLD}=== Redictum E2E Tests ===${NC}"

# Start Xvfb virtual display
Xvfb :99 -screen 0 1024x768x24 &>/dev/null &
XVFB_PID=$!
export DISPLAY=:99
sleep 0.5

if ! kill -0 "$XVFB_PID" 2>/dev/null; then
    echo -e "${RED}Failed to start Xvfb${NC}"
    exit 1
fi

trap 'cleanup_test 2>/dev/null; kill $XVFB_PID 2>/dev/null' EXIT

# Run all tests
run_test "T01 Clean first run"      test_01_clean_first_run
run_test "T02 Daemon starts"        test_02_daemon_starts
run_test "T03 Status (running)"     test_03_status_running
run_test "T04 Double start"         test_04_double_start
run_test "T05 Stop daemon"          test_05_stop_daemon
run_test "T06 Status (not running)" test_06_status_not_running
run_test "T07 Stale PID"            test_07_stale_pid
run_test "T08 Config reset"         test_08_config_reset
run_test "T09 Restart cycle"        test_09_restart_cycle
run_test "T10 SIGTERM graceful"     test_10_sigterm_graceful

# Summary
echo -e "\n${BOLD}==============================${NC}"
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo -e "${BOLD}==============================${NC}"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
