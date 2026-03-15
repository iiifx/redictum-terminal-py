# Feature: --verbose and --quiet CLI flags

> Обновлено: 2026-02-24
> Статус: утверждён

## Problem

Currently there's no way to control output verbosity:
- Interactive mode always prints the same amount of output
- No way to get more debug info when troubleshooting
- No way to suppress output for scripting/automation

## Desired behavior

### --quiet (-q)

Full automation mode. Suppress all `_rprint()` output + auto-answer prompts with defaults.

Only visible output:
- Fatal errors (stderr via `RedictumError`)
- Transcribed text (if not auto-pasting)

Prompts (`_confirm`): return `default` value without asking.
`input()` prompts: return default/empty (triggers EOF path → default choice).

Use case: automated installation with defaults, running in tmux, scripting.

### --verbose (-v)

Print additional diagnostic info via `_rprint(..., level=1)`:
- Dependency check details (versions, paths)
- Recording duration
- Audio RMS values
- Whisper CLI command being run
- Transcription timing
- Clipboard save/restore details

In daemon mode: sets logging level to DEBUG in the log file.

Use case: debugging issues, understanding what's happening.

### Default (no flag)

Current behavior — status messages, banners, dependency checks.

## Implementation

### Global verbosity level

Module-level variable instead of per-instance:

```python
_verbosity = 0  # -1 = quiet, 0 = normal, 1 = verbose
```

### _rprint() changes

Add optional `level` parameter:

```python
def _rprint(text: str, level: int = 0) -> None:
    if _verbosity < 0 and level < 1:  # quiet: suppress normal output
        return
    if level > 0 and _verbosity < level:  # verbose-only: suppress unless verbose
        return
    # print as before
```

Existing 168+ calls untouched (level=0 by default).
New verbose messages: `_rprint("...", level=1)` in ~10-15 pipeline locations.

### _confirm() changes

```python
def _confirm(prompt, default=False):
    if _verbosity < 0:  # quiet mode
        return default
    # ... existing code
```

### input() prompts in quiet mode

Wizards that use raw `input()` (model selector, language wizard):
- In quiet mode, raise EOFError → existing EOF handlers return default.
- OR: wrap in helper that checks `_verbosity`.

### Language command in quiet mode

Special case: `./redictum -q language` → skip wizard, set `("auto", "auto")` directly.

### CLI registration

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
group.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (auto-answer prompts with defaults)")
```

### RedictumApp constructor

```python
def __init__(self, script_dir, overrides=None, verbose=False, quiet=False):
    global _verbosity
    if quiet:
        _verbosity = -1
    elif verbose:
        _verbosity = 1
```

## Prompt audit (quiet mode — all auto-default)

### Interactive first run (`./redictum -q`)
| Prompt | Default | Result |
|--------|---------|--------|
| Install missing dependencies? | Y | installs xclip, pynput |
| Install paplay? | Y | installs |
| Install ffmpeg? | Y | installs |
| Install xdotool? | Y | installs |
| Install whisper.cpp? | Y | installs |
| Install build tools (cmake)? | Y | installs |
| Install CUDA toolkit? | Y | installs (~4 GB, acceptable) |
| Select model [1-N, default=1] | 1 | picks recommended model |
| Change language? (first run) | N | keeps auto-detected |

### Commands
| Command | Prompt | Default | Result |
|---------|--------|---------|--------|
| `-q setup` | optional deps | Y | installs all |
| `-q whisper` | Rebuild? | N | no rebuild |
| `-q whisper` | Change model? | N | keeps current |
| `-q language` | (no prompts) | — | sets ("auto","auto") directly |
| `-q update` | Update? | Y | updates if newer |
| `-q start` | (none) | — | starts daemon silently |
| `-q stop` | (none) | — | stops daemon silently |

## Verification

- `./redictum -q` → silent first-run setup, all defaults applied
- `./redictum -q` → minimal output in working mode
- `./redictum -v` → extra diagnostic info visible
- `./redictum -q start` → daemon starts silently
- `./redictum -q language` → sets auto without wizard
- `./redictum -q update` → auto-confirms update
- `./redictum -q -v` → error (mutually exclusive)
- All existing E2E tests pass (they don't use these flags)
