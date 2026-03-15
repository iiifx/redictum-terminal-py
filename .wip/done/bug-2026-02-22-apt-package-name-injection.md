# Bug: No validation on apt package names in _install_apt()

**Source:** Copilot security audit PR #2
**Severity:** MEDIUM (defense-in-depth)
**Status:** pending

## Problem

`Diagnostics._install_apt(packages)` passes package names directly to
`sudo apt install -y` without validation. If a malicious value somehow
reaches this method, it could inject shell-significant characters.

```python
def _install_apt(self, packages: list[str]) -> bool:
    cmd = ["sudo", "apt", "install", "-y", *packages]
    # no validation on package names
```

## Current risk assessment

**Low in practice** — all package names come from hardcoded dicts:
- `APT_PACKAGES = {"xclip": "xclip"}`
- `PIP_APT_FALLBACK = {"pynput": "python3-pynput"}`
- Optional: `["pulseaudio-utils"]`, `["ffmpeg"]`, `["xdotool"]`

No user input reaches `_install_apt()` directly. But defense-in-depth is
good practice — if future code adds user-configurable packages, the
validation is already in place.

## Proposed fix

Add regex validation at the top of `_install_apt()`:

```python
import re

for pkg in packages:
    if not pkg or len(pkg) < 2:
        logging.error("Invalid package name (too short): %s", pkg)
        return False
    if not re.match(r'^[a-z0-9][a-z0-9+.-]+$', pkg):
        logging.error("Invalid package name: %s", pkg)
        return False
```

Debian package naming policy: starts with alphanumeric, only `[a-z0-9+.-]`.

## Notes

- `re` is already imported in the script
- Copilot's regex looks correct for Debian package names
- Should also cover `_ensure_build_tools()` which calls `_install_apt(["cmake"])`
