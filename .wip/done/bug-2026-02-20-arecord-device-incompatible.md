# BUG: arecord -D pulse не работает на некоторых системах

> Дата: 2026-02-20
> Источник: логи тестировщика
> Статус: анализ
> Приоритет: высокий

## Проблема

Дефолтное устройство записи в конфиге — `device: "pulse"`. На системах без PulseAudio (или с PipeWire без pulse-совместимости) `arecord -D pulse` стартует и мгновенно умирает, выдавая пустой WAV.

## Подтверждение из реальных логов

12 попыток записи — все мгновенно провалены:

```
17:38:15 [INFO] Recording started: rec_20260220_173815.wav
17:38:15 [WARNING] Recording produced no audio    ← в ту же секунду
```

arecord стартует и тут же завершается. Файл пустой или с минимальным WAV-заголовком.

## Причина

- `arecord -D pulse` требует PulseAudio или PipeWire с `pipewire-pulse` модулем
- На чистых PipeWire-системах (Fedora 38+, Ubuntu 23.04+ могут не иметь pulse-совместимости)
- На системах без звукового сервера вообще

Наш Stage 1 проверяет `shutil.which("arecord")` — бинарник есть, проверка проходит. Но устройство `pulse` может быть недоступно.

## Варианты фикса

### A. Проверять устройство при запуске

Добавить в Stage 1 или при первом запуске пробную запись (0.1 сек):

```python
def _check_audio_device(self, device: str) -> bool:
    """Test if arecord can record from the given device."""
    test_file = Path(tempfile.mktemp(suffix=".wav"))
    try:
        result = subprocess.run(
            ["arecord", "-D", device, "-f", "S16_LE",
             "-r", "16000", "-c", "1", "-d", "0",  # 0 = мгновенно
             "-t", "wav", str(test_file)],
            capture_output=True, timeout=3,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    finally:
        test_file.unlink(missing_ok=True)
```

### B. Автоопределение устройства

Попробовать `pulse`, если не работает — `default`, если не работает — первое устройство из `arecord -L`:

```python
DEVICE_CANDIDATES = ["pulse", "default", "plughw:0,0"]

def _find_working_device(self) -> str | None:
    for device in DEVICE_CANDIDATES:
        if self._check_audio_device(device):
            return device
    return None
```

### C. Понятное сообщение об ошибке

Если устройство не работает — сказать пользователю что проверить:

```
[red]✗[/red] Audio device 'pulse' is not accessible.
  Try: pactl info          (check PulseAudio)
  Try: arecord -D default  (test default device)
  Config: audio.recording.device in config.yaml
```

## Рекомендация

Комбо A + C: проверить устройство при первом запуске, при ошибке — понятное сообщение с инструкцией. Автоопределение (B) — бонус.
