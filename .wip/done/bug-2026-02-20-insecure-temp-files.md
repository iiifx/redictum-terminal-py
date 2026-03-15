# Bug: Предсказуемые имена tmp-файлов + неполный cleanup

**Приоритет:** HIGH
**Источник:** GitHub Copilot Security Audit (PR #1)

## Описание

В двух местах используются предсказуемые имена временных файлов:

1. **CUDA keyring** (`_install_cuda()`, строка ~784):
   ```python
   keyring_deb = Path(tempfile.gettempdir()) / "cuda-keyring.deb"
   ```

2. **Whisper tarball** (`_clone()`, строка ~836):
   ```python
   tarball = Path(tempfile.gettempdir()) / "whisper.cpp.tar.gz"
   ```

### Проблемы:

- **Предсказуемое имя** — атакующий с локальным доступом может подложить свой `.deb` или `.tar.gz` между скачиванием и использованием (TOCTOU race condition)
- **Неполный cleanup** — при ошибке на промежуточном шаге файл может остаться в `/tmp`
- Для `.deb` — выполняется через `sudo dpkg -i`, что усиливает ущерб

## Решение

Заменить на `tempfile.mkstemp()` + обернуть в `try-finally`:

```python
# Вместо:
keyring_deb = Path(tempfile.gettempdir()) / "cuda-keyring.deb"

# Использовать:
fd, keyring_path = tempfile.mkstemp(suffix=".deb", prefix="cuda-keyring-")
keyring_deb = Path(keyring_path)
os.close(fd)

try:
    # ... download and install ...
finally:
    keyring_deb.unlink(missing_ok=True)
```

Аналогично для `whisper.cpp.tar.gz`.
