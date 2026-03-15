# BUG: Зомби-процессы paplay при воспроизведении звуков

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: средний

## Проблема

`SoundNotifier._play()` вызывает `Popen` для `paplay`, но никогда не вызывает `.wait()`. Каждый звук создаёт дочерний процесс, который после завершения становится зомби до сборки мусора Python. За длинную сессию демона накапливаются зомби.

## Код

Строки 1552-1558:
```python
subprocess.Popen(
    ["paplay", f"--volume={vol_scaled}", str(wav_path)],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)   # ← fire-and-forget, нет .wait()
```

## Фикс

Запускать `.wait()` в фоновом потоке:

```python
def _play(self, name: str) -> None:
    ...
    try:
        proc = subprocess.Popen(
            ["paplay", f"--volume={vol_scaled}", str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        threading.Thread(target=proc.wait, daemon=True).start()
    except FileNotFoundError:
        pass
```
