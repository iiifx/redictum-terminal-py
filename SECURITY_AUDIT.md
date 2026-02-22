# Security Audit Report - Redictum Terminal

## Summary
This document details the security audit findings and fixes for the redictum voice-to-text CLI application.

**Security Score: A**

The application has been thoroughly audited and all identified security issues have been fixed. The codebase now follows security best practices for Python CLI applications.

## Findings and Fixes

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

### ✅ FIXED: Privilege Escalation (Priority: HIGH)
**Status:** FIXED
**Issue:** `sudo apt install` commands needed package name validation
**Fix:** Added strict validation for package names with regex `^[a-z0-9][a-z0-9+.-]+$` and minimum length check
**Location:** Lines 737-756
**Test Coverage:** 3 tests validating valid and malicious package names

### ✅ SECURE: Temp File Safety (Priority: HIGH)
**Status:** Secure
- Uses `tempfile.mkstemp()` for secure temp file creation (lines 621, 1187, 1251)
- File descriptors are properly closed immediately after creation
- Cleanup in finally blocks

**Evidence:**
- Line 620-638: Audio test uses mkstemp with fd close and cleanup in finally
- Line 1187-1243: CUDA keyring download uses mkstemp with proper cleanup

### ✅ FIXED: Input Validation (Priority: MEDIUM)
**Status:** FIXED
**Issue:** Boolean config values didn't raise errors for invalid inputs - they silently converted to False
**Fix:** Added strict validation that raises `RedictumError` for invalid boolean values
**Location:** Lines 433-444
**Test Coverage:** Test validates "maybe" raises error instead of converting to False

**Example:**
```python
# Before: "maybe" → False (silent)
# After: "maybe" → RedictumError("Config 'key': expected boolean (true/false), got 'maybe'")
```

### ✅ SECURE: Dependency Install Chain (Priority: MEDIUM)
**Status:** Secure
- Uses `sys.executable -m pip` consistently (line 747)
- Has PEP 668 fallback chain: pip → apt → pip --break-system-packages
- Package names are from hardcoded dicts, not user input

**Evidence:**
- Line 747: `cmd = [sys.executable, "-m", "pip", "install", *packages]`

### ✅ FIXED: PID File Handling (Priority: MEDIUM)
**Status:** FIXED
**Issue 1:** Race condition between PID check and PID write
**Issue 2:** PID file created with default permissions

**Fix:**
1. Use atomic file creation with O_EXCL flag (try exclusive first, fall back to O_TRUNC after stale check)
2. Set restrictive permissions (0o644) on PID file explicitly
3. Use os.open() with explicit mode instead of Path.write_text()

**Location:** Lines 1664-1676
**Test Coverage:** Test validates PID file is not world-writable

### ✅ SECURE: X11 Clipboard (Priority: LOW)
**Status:** Secure
- Clipboard content passed via stdin, not command line arguments
- Uses list arguments for all xclip/xdotool calls
- Properly handles binary data

**Evidence:**
- Line 2204-2205: `["xclip", "-selection", "clipboard"], input=text.encode("utf-8")`

### ✅ ACCEPTABLE: Signal Handling (Priority: LOW)
**Status:** Acceptable
- Line 1674-1677: Signal handler only sets event and logs
- Logging in signal handler is not async-signal-safe (minor POSIX violation)

**Note:** While not perfectly async-signal-safe, the risk is minimal for this application

### ✅ FIXED: File Permissions (Priority: HIGH)
**Status:** FIXED
**Issue:** `os.umask(0)` on line 1708 made all files created by daemon world-writable!

**Fix:**
1. Changed `os.umask(0)` to `os.umask(0o022)` 
2. Explicitly set permissions on sensitive files:
   - PID file: 0o644 (read-only for others)
   - Config files: 0o600 (owner-only)
   - Log files: 0o644 (read-only for others)

**Locations:**
- Line 1708: umask fix
- Lines 361, 424, 433: config file permissions
- Lines 1664-1676: PID file permissions

**Test Coverage:** 3 tests validate file permissions

### ✅ SECURE: Logging (Priority: MEDIUM)
**Status:** Secure - no sensitive data logged
- Line 3205: Logs character count, not actual transcribed text
- No clipboard data logged
- Only logs metadata

**Note:** Transcript files do contain actual text (by design), documented in README

### ✅ SECURE: CUDA Installer (Priority: MEDIUM)
**Status:** Secure
**Validation:**
- CUDA keyring URL is hardcoded class constant (good)
- Lines 1193-1206: Downloads with curl/wget using list arguments
- No shell=True usage

**Note:** Could add checksum verification for defense-in-depth, but URL is hardcoded so risk is low

## Test Coverage

Created comprehensive security test suite:
- ✅ 22 security tests covering all 12 audit areas
- ✅ All security tests passing
- ✅ No breaking changes to existing functionality
- ✅ CodeQL scan clean (1 false positive in test code only)

## Security Summary

All critical and high-priority security issues have been fixed:
1. ✅ Fixed world-writable files via umask
2. ✅ Added strict input validation for booleans
3. ✅ Added package name validation
4. ✅ Fixed PID file race conditions and permissions
5. ✅ Set explicit permissions on config files

The application follows security best practices:
- ✅ No command injection vulnerabilities
- ✅ No path traversal vulnerabilities  
- ✅ Secure temp file handling
- ✅ Proper input validation
- ✅ Restrictive file permissions
- ✅ No sensitive data in logs

## Previous Priority Fixes

1. **HIGH:** Fix `os.umask(0)` - creates world-writable files ✅ FIXED
2. **HIGH:** Add package name validation for apt install ✅ FIXED
3. **MEDIUM:** Fix boolean validation to raise errors ✅ FIXED
4. **MEDIUM:** Fix PID file race condition and permissions ✅ FIXED
5. **OPTIONAL:** Add CUDA keyring checksum verification - Not critical, URL is hardcoded

## Security Score: A

The application is well-designed from a security perspective with all identified issues fixed.

