# Security Audit Report - Redictum Terminal

## Summary
This document details the security audit findings for the redictum voice-to-text CLI application.

## Findings

### ✅ SECURE: Command Injection (Priority: CRITICAL)
**Status:** No vulnerabilities found
- All `subprocess.run()` calls use list arguments, not shell strings
- No `shell=True` usage found anywhere in the codebase
- User-controlled paths (whisper_cli, whisper_model) are passed as list elements
- Clipboard content is passed via stdin as bytes, not shell interpolation
- xclip/xdotool commands properly use list arguments

**Evidence:**
- Line 2136-2163: Transcriber uses `cmd = [self._cli, "-m", self._model, ...]`
- Line 2203-2209: Clipboard copy uses `["xclip", "-selection", "clipboard"]` with `input=text.encode()`
- Line 2221-2226: xdotool uses `["xdotool", "key", "--clearmodifiers", "ctrl+v"]`

### ✅ SECURE: Path Traversal (Priority: HIGH)
**Status:** No vulnerabilities found
- Config paths with `~` are properly expanded via `Path.expanduser()`
- All paths are resolved relative to script_dir or user home
- No direct user input for path construction without validation

**Evidence:**
- Line 490-505: `_expand_paths()` properly expands tildes and validates paths
- Line 2094-2101: Transcriber validates paths exist and are executable/readable

### ⚠️ NEEDS FIX: Privilege Escalation (Priority: HIGH)
**Issue:** `sudo apt install` commands use list arguments (secure), but package names from dicts could theoretically be modified
**Recommendation:** Add validation for package names to ensure they match expected patterns

**Location:** Lines 780-781, 1224-1226
**Fix:** Add package name validation with regex `^[a-z0-9][a-z0-9+.-]+$`

### ✅ SECURE: Temp File Safety (Priority: HIGH)
**Status:** Mostly secure
- Uses `tempfile.mkstemp()` for secure temp file creation (lines 621, 1187, 1251)
- File descriptors are properly closed immediately after creation
- Cleanup in finally blocks

**Evidence:**
- Line 620-638: Audio test uses mkstemp with fd close and cleanup in finally
- Line 1187-1243: CUDA keyring download uses mkstemp with proper cleanup

### ⚠️ NEEDS FIX: Input Validation (Priority: MEDIUM)
**Issue:** Boolean config values don't raise errors for invalid inputs - they silently convert to False
**Location:** Line 434: `return value.lower() in ("true", "yes", "1", "on")`
**Fix:** Should raise RedictumError for invalid boolean values like "maybe", "invalid", etc.

**Example:**
```python
# Current: "maybe" → False (silent)
# Should: "maybe" → RedictumError("Config 'key': expected boolean, got 'maybe'")
```

### ✅ SECURE: Dependency Install Chain (Priority: MEDIUM)
**Status:** Secure
- Uses `sys.executable -m pip` consistently (line 747)
- Has PEP 668 fallback chain: pip → apt → pip --break-system-packages
- Package names are from hardcoded dicts, not user input

**Evidence:**
- Line 747: `cmd = [sys.executable, "-m", "pip", "install", *packages]`

### ⚠️ NEEDS FIX: PID File Handling (Priority: MEDIUM)
**Issue 1:** Race condition between PID check and PID write
- Lines 1688-1695: Check if PID exists, clean stale, then fork
- Window between check and write where another process could start

**Issue 2:** PID file created with default permissions (may be world-writable depending on umask)
- Line 1658: Uses `write_text()` without explicit permissions
- Line 1708: Sets `os.umask(0)` which makes all subsequent files world-writable!

**Fix:**
1. Use atomic file creation with O_EXCL flag
2. Set restrictive permissions (0o644) on PID file
3. Fix umask to something reasonable (0o022) or set permissions explicitly

### ✅ MOSTLY SECURE: X11 Clipboard (Priority: LOW)
**Status:** Secure
- Clipboard content passed via stdin, not command line arguments
- Uses list arguments for all xclip/xdotool calls
- Properly handles binary data

**Evidence:**
- Line 2204-2205: `["xclip", "-selection", "clipboard"], input=text.encode("utf-8")`

### ⚠️ ADVISORY: Signal Handling (Priority: LOW)
**Status:** Acceptable but could be improved
- Line 1674-1677: Signal handler only sets event and logs
- Logging in signal handler is not async-signal-safe (POSIX violation)

**Recommendation:** Use only async-signal-safe operations in signal handlers

### ⚠️ NEEDS FIX: File Permissions (Priority: HIGH)
**Issue:** `os.umask(0)` on line 1708 makes all files created by daemon world-writable!
- Log files created with 0o644 (line 1728) but umask(0) means this is: rwxrw-rw-
- PID file has no explicit permissions
- Config files have no explicit permissions

**Fix:**
1. Change `os.umask(0)` to `os.umask(0o022)` 
2. Explicitly set permissions on sensitive files: PID (0o644), config (0o600), logs (0o600)

### ⚠️ ADVISORY: Logging (Priority: MEDIUM)
**Status:** Good - no sensitive data logged
- Line 3205: Logs character count, not actual transcribed text
- No clipboard data logged
- Only logs metadata

**Recommendation:** Consider adding a privacy notice that transcript files contain actual text

### ⚠️ NEEDS REVIEW: CUDA Installer (Priority: MEDIUM)
**Issue:** CUDA keyring URL is hardcoded (good) but download not verified
- Line 1151: Hardcoded URL format (secure)
- Lines 1193-1206: Downloads with curl/wget but no checksum verification

**Recommendation:** Add checksum verification for downloaded keyring package

## Priority Fixes Required

1. **HIGH:** Fix `os.umask(0)` - creates world-writable files
2. **HIGH:** Add package name validation for apt install
3. **MEDIUM:** Fix boolean validation to raise errors
4. **MEDIUM:** Fix PID file race condition and permissions
5. **MEDIUM:** Add CUDA keyring checksum verification (optional but recommended)

## Security Score: B+

The application is generally well-designed from a security perspective:
- ✅ No command injection vulnerabilities
- ✅ No path traversal vulnerabilities  
- ✅ Secure temp file handling
- ⚠️ File permissions issue (umask) needs immediate fix
- ⚠️ Input validation could be stricter

## Recommendations

1. **Immediate:** Fix umask to 0o022
2. **High Priority:** Add input validation for booleans
3. **Medium Priority:** Fix PID file race condition
4. **Optional:** Add checksum verification for downloads
5. **Documentation:** Add privacy notice about transcript logging
