# Bug: Отсутствие валидации путей в Transcriber

**Приоритет:** MEDIUM
**Источник:** GitHub Copilot Security Audit (PR #1)

## Описание

В `Transcriber.__init__()` (строка ~1345) пути к whisper CLI и модели сохраняются без проверки:

```python
self._cli = whisper_cli
self._model = model_path
```

Если в `config.yaml` указан несуществующий путь или путь к не-файлу, ошибка проявится только при вызове `transcribe()` — с невнятным сообщением от subprocess.

## Примечание

Copilot предложил полную symlink-валидацию с allowlist директорий (`/home`, `/usr`, `/opt`, `/var`) — это избыточно для CLI-утилиты, где пользователь сам контролирует конфиг. Allowlist может сломать легитимные установки в `/snap`, `/mnt`, `/data` и т.д.

## Решение (упрощённое)

Добавить базовые проверки без symlink-паранойи:

```python
def __init__(self, whisper_cli, model_path, ...):
    cli = Path(whisper_cli)
    if not cli.exists():
        raise RedictumError(f"Whisper CLI not found: {cli}")
    if not os.access(cli, os.X_OK):
        raise RedictumError(f"Whisper CLI is not executable: {cli}")

    model = Path(model_path)
    if not model.is_file():
        raise RedictumError(f"Whisper model not found: {model}")

    self._cli = str(cli)
    self._model = str(model)
```

Понятные ошибки на старте вместо невнятного падения позже. Без лишнего over-engineering.
