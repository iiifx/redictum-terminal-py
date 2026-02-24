#!/bin/bash
# =============================================================================
# Redictum Terminal — E2E Test Suite (Docker)
# =============================================================================
# Runs 18 daemon lifecycle + update + verbosity tests in a clean Docker container.
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

# Create a pre-initialized environment so run_start() passes the guard.
# Daemon mode no longer runs init() — it requires prior interactive setup.
prepare_env() {
    echo '{"initialized_at": "2024-01-01T00:00:00", "version": "1.0.0"}' > "$WORKDIR/.state"
    touch "$WORKDIR/fake-model.bin"
    cat > "$WORKDIR/config.ini" <<CONF
[dependency]
whisper_cli = "/usr/local/bin/whisper-cli"
whisper_model = "$WORKDIR/fake-model.bin"
whisper_language = "auto"
whisper_prompt = "auto"
whisper_timeout = 120

[audio]
recording_device = "pulse"
recording_normalize = true
recording_silence_detection = true
recording_silence_threshold = 200
recording_volume_reduce = true
recording_volume_level = 30

[input]
hotkey_key = "Insert"
hotkey_hold_delay = 0.6
hotkey_translate_key = "ctrl+Insert"

[clipboard]
paste_auto = true
paste_prefix = ""
paste_postfix = " "
paste_restore_delay = 0.3

[notification]
sound_signal_volume = 30
sound_signal_start = true
sound_signal_processing = false
sound_signal_done = true
sound_signal_error = true

[storage]
audio_max_files = 50
transcripts_max_files = 50
logs_max_files = 50
CONF
    mkdir -p "$WORKDIR/audio" "$WORKDIR/transcripts" "$WORKDIR/logs"
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
    rm -f "$WORKDIR/config.ini" "$WORKDIR/config.ini.bak" "$WORKDIR/.state" "$WORKDIR/redictum.pid"
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

# T01: Daemon refuses to start without prior initialization
test_01_start_refuses_without_init() {
    local output
    output=$(python3 "$SCRIPT" start </dev/null 2>&1)
    local rc=$?
    assert_exit_error $rc || return 1
    assert_contains "$output" "not initialized" || return 1
    assert_file_missing "$WORKDIR/.state" || return 1
    assert_file_missing "$WORKDIR/config.ini" || return 1
}

# T02: Daemon starts — PID file exists and process is alive
test_02_daemon_starts() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1

    assert_file_exists "$WORKDIR/redictum.pid" || return 1
    local pid
    pid=$(read_pid)
    assert_pid_alive "$pid" || return 1
}

# T03: Status shows running + PID
test_03_status_running() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    local pid
    pid=$(read_pid)

    local output
    output=$(python3 "$SCRIPT" status 2>&1)
    assert_contains "$output" "running" || return 1
    assert_contains "$output" "$pid" || return 1
}

# T04: Double start — second start fails with "already running"
test_04_double_start() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1

    local output
    output=$(python3 "$SCRIPT" start </dev/null 2>&1)
    local rc=$?
    assert_exit_error $rc || return 1
    assert_contains "$output" "already running" || return 1
}

# T05: Stop daemon — PID file removed, process dead
test_05_stop_daemon() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
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
    prepare_env
    echo "99999" > "$WORKDIR/redictum.pid"

    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1

    local pid
    pid=$(read_pid)
    if [[ "$pid" == "99999" ]]; then
        echo -e "  ${RED}FAIL${NC}: PID should not be 99999 (stale not cleaned)"
        return 1
    fi
    assert_pid_alive "$pid" || return 1
}

# T08: --config + start refuses (--config deletes .state, daemon requires init)
test_08_config_start_refuses() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    local pid
    pid=$(read_pid)

    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    wait_for_pid_gone "$pid" || return 1

    # --config deletes .state + config.ini → start must refuse
    local output
    output=$(python3 "$SCRIPT" --config start </dev/null 2>&1)
    local rc=$?
    assert_exit_error $rc || return 1
    assert_contains "$output" "not initialized" || return 1
}

# T09: Restart cycle — stop then start, PID alive
test_09_restart_cycle() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
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
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    local pid
    pid=$(read_pid)

    kill -TERM "$pid"
    wait_for_pid_gone "$pid" || return 1
    sleep 0.5  # let atexit cleanup run
    assert_file_missing "$WORKDIR/redictum.pid" || return 1
}

# T11: --set overrides config values at runtime (no sed needed)
test_11_set_overrides() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    local pid
    pid=$(read_pid)
    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    wait_for_pid_gone "$pid" || return 1

    # Start with --set overriding whisper paths (instead of fix_whisper_config)
    touch "$WORKDIR/set-model.bin"
    python3 "$SCRIPT" \
        --set "dependency.whisper_cli=/usr/local/bin/whisper-cli" \
        --set "dependency.whisper_model=$WORKDIR/set-model.bin" \
        start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1

    local pid2
    pid2=$(read_pid)
    assert_pid_alive "$pid2" || return 1
    rm -f "$WORKDIR/set-model.bin"
}

# T12: --set with unknown key exits with error
test_12_set_invalid_key() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    local pid
    pid=$(read_pid)
    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    wait_for_pid_gone "$pid" || return 1

    local output
    output=$(python3 "$SCRIPT" --set "nonexistent.key=val" start </dev/null 2>&1)
    local rc=$?
    assert_exit_error $rc || return 1
    assert_contains "$output" "Unknown section" || return 1
}

# T13: --set with bad format (no =) exits with error
test_13_set_bad_format() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1
    local pid
    pid=$(read_pid)
    python3 "$SCRIPT" stop </dev/null >/dev/null 2>&1
    wait_for_pid_gone "$pid" || return 1

    local output
    output=$(python3 "$SCRIPT" --set "dependency.whisper_language" start </dev/null 2>&1)
    local rc=$?
    assert_exit_error $rc || return 1
    assert_contains "$output" "Invalid --set format" || return 1
}

# =============================================================================
# Update test helpers
# =============================================================================

# Extract VERSION from the script
SCRIPT_VERSION=$(python3 -c "
import sys; sys.path.insert(0, '$WORKDIR')
exec(open('$SCRIPT').read().split('class ')[0])
print(VERSION)
" 2>/dev/null)

# Create a fake curl that serves update-related URLs
setup_fake_curl() {
    local fake_version="$1"
    local fake_curl_dir="$WORKDIR/fake-curl-bin"
    mkdir -p "$fake_curl_dir"

    # Build a fake script to serve as the "new version"
    local fake_new_script="$WORKDIR/fake-new-redictum"
    cp "$SCRIPT" "$fake_new_script"
    local real_hash
    real_hash=$(sha256sum "$fake_new_script" | awk '{print $1}')

    cat > "$fake_curl_dir/curl" <<FAKECURL
#!/usr/bin/env python3
import sys, os, json, shutil

args = sys.argv[1:]

# Parse -o flag
output_file = None
url = None
for i, a in enumerate(args):
    if a == "-o" and i + 1 < len(args):
        output_file = args[i + 1]
    elif not a.startswith("-"):
        url = a

if url is None:
    sys.exit(1)

if "releases/latest" in url:
    print(json.dumps({"tag_name": "v${fake_version}"}))
    sys.exit(0)

if url.endswith(".sha256"):
    if output_file:
        with open(output_file, "w") as f:
            f.write("${real_hash}  redictum\\n")
    else:
        print("${real_hash}  redictum")
    sys.exit(0)

if "/redictum" in url and not url.endswith(".sha256"):
    if output_file:
        shutil.copy("${fake_new_script}", output_file)
    sys.exit(0)

# Fallback: call real curl
os.execvp("/usr/bin/curl", ["/usr/bin/curl"] + args)
FAKECURL
    chmod +x "$fake_curl_dir/curl"
}

cleanup_fake_curl() {
    rm -rf "$WORKDIR/fake-curl-bin" "$WORKDIR/fake-new-redictum"
}

# T14: Update — already up to date
test_14_update_already_up_to_date() {
    prepare_env
    setup_fake_curl "$SCRIPT_VERSION"
    local output
    output=$(PATH="$WORKDIR/fake-curl-bin:$PATH" python3 "$SCRIPT" update </dev/null 2>&1)
    local rc=$?
    cleanup_fake_curl
    assert_exit_ok $rc || return 1
    assert_contains "$output" "up to date" || return 1
}

# T15: Update — daemon is running
test_15_update_daemon_running() {
    prepare_env
    python3 "$SCRIPT" start </dev/null >/dev/null 2>&1
    wait_for_daemon || return 1

    setup_fake_curl "99.0.0"
    local output
    output=$(echo "y" | PATH="$WORKDIR/fake-curl-bin:$PATH" python3 "$SCRIPT" update 2>&1)
    local rc=$?
    cleanup_fake_curl
    assert_exit_error $rc || return 1
    assert_contains "$output" "stop" || return 1
}

# T16: Update — user declines (EOF)
test_16_update_user_declines_eof() {
    prepare_env
    setup_fake_curl "99.0.0"
    local output
    output=$(PATH="$WORKDIR/fake-curl-bin:$PATH" python3 "$SCRIPT" update </dev/null 2>&1)
    local rc=$?
    cleanup_fake_curl
    assert_exit_ok $rc || return 1
    assert_contains "$output" "99.0.0" || return 1
}

# T17: Quiet first-run — creates config and state with defaults, minimal output
test_17_quiet_first_run() {
    local output
    output=$(python3 "$SCRIPT" -q </dev/null 2>&1)
    local rc=$?
    assert_exit_ok $rc || return 1
    assert_file_exists "$WORKDIR/config.ini" || return 1
    assert_file_exists "$WORKDIR/.state" || return 1
}

# T18: Quiet start/stop — daemon starts and stops with no output
test_18_quiet_start_stop() {
    prepare_env
    python3 "$SCRIPT" -q start </dev/null >/dev/null 2>&1
    local rc=$?
    assert_exit_ok $rc || return 1
    wait_for_daemon || return 1

    python3 "$SCRIPT" -q stop </dev/null >/dev/null 2>&1
    rc=$?
    assert_exit_ok $rc || return 1
    local pid
    pid=$(read_pid 2>/dev/null)
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        echo -e "  ${RED}FAIL${NC}: daemon still running after quiet stop"
        return 1
    fi
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
run_test "T01 Start refuses w/o init" test_01_start_refuses_without_init
run_test "T02 Daemon starts"        test_02_daemon_starts
run_test "T03 Status (running)"     test_03_status_running
run_test "T04 Double start"         test_04_double_start
run_test "T05 Stop daemon"          test_05_stop_daemon
run_test "T06 Status (not running)" test_06_status_not_running
run_test "T07 Stale PID"            test_07_stale_pid
run_test "T08 --config start refuses" test_08_config_start_refuses
run_test "T09 Restart cycle"        test_09_restart_cycle
run_test "T10 SIGTERM graceful"     test_10_sigterm_graceful
run_test "T11 --set overrides"      test_11_set_overrides
run_test "T12 --set invalid key"    test_12_set_invalid_key
run_test "T13 --set bad format"     test_13_set_bad_format
run_test "T14 Update: up to date"  test_14_update_already_up_to_date
run_test "T15 Update: daemon running" test_15_update_daemon_running
run_test "T16 Update: EOF decline" test_16_update_user_declines_eof
run_test "T17 Quiet first-run"   test_17_quiet_first_run
run_test "T18 Quiet start/stop"  test_18_quiet_start_stop

# Summary
echo -e "\n${BOLD}==============================${NC}"
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo -e "${BOLD}==============================${NC}"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
