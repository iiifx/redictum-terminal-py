# BUG: Звуки генерируются при старте даже если все отключены

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: низкий

## Проблема

`SoundNotifier.__init__` всегда синтезирует 4 WAV-файла и записывает во временную директорию, даже если в конфиге все `signal_*: false`.

## Код

Строки 1521-1522:
```python
def __init__(self, volume: int = 30) -> None:
    self._volume = max(0, min(100, volume))
    self._temp_dir = Path(tempfile.mkdtemp(prefix="redictum_"))
    self._sounds: dict[str, Path] = {}
    for name, samples in _generate_tones().items():
        self._sounds[name] = self._write_wav(f"{name}.wav", samples)
```

## Фикс

Ленивая генерация — создавать WAV только при первом вызове `play()`:

```python
def _ensure_tone(self, name: str) -> Path:
    if name not in self._sounds:
        tones = _generate_tones()
        self._sounds[name] = self._write_wav(f"{name}.wav", tones[name])
    return self._sounds[name]
```

Или проверять конфиг и не создавать `SoundNotifier` вообще, если все звуки отключены.
