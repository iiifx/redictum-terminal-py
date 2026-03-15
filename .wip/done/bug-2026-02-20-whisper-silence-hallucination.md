# BUG: Whisper галлюцинирует на тишине

> Дата: 2026-02-20
> Источник: собственное тестирование
> Статус: анализ

## Симптомы

Зажать кнопку, ничего не сказать, отпустить. Whisper вместо пустого результата выдаёт случайный текст — "галлюцинации".

Примеры типичных галлюцинаций:
- "Субтитры сделал DimaTorzworworworworworworwor"
- "Thanks for watching!"
- "Подписывайтесь на канал"
- Повторяющиеся фразы из prompt
- Случайные слова на разных языках

## Текущая защита

В коде уже есть `BLANK_MARKERS` (строка 1336):

```python
BLANK_MARKERS = {"[BLANK_AUDIO]", "[ЗВУК]", "(silence)"}
```

Проверка (строка 1401):
```python
if not text or text in self.BLANK_MARKERS:
    return ""
```

Этого недостаточно — whisper часто галлюцинирует текстом, который НЕ совпадает ни с одним маркером.

## Варианты решения

### A. Проверка энергии аудио (VAD — Voice Activity Detection)

Перед отправкой в whisper проверить, есть ли в записи реальный звук:

```python
import struct

def _has_voice(wav_path: Path, threshold: float = 500.0) -> bool:
    """Check if WAV contains audio above silence threshold."""
    with open(wav_path, "rb") as f:
        f.seek(44)  # skip WAV header
        data = f.read()
    if not data:
        return False
    samples = struct.unpack(f"<{len(data)//2}h", data)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return rms > threshold
```

Плюсы: не запускаем whisper вообще — экономим время.
Минусы: нужно подобрать threshold, может отсечь тихую речь.

### B. Минимальная длина записи

Если запись короче N секунд (например, 0.5с) — считать тишиной и не транскрибировать.

```python
MIN_RECORDING_SECONDS = 0.5

duration = audio_path.stat().st_size / (AUDIO_SAMPLE_RATE * 2)  # 16-bit mono
if duration < MIN_RECORDING_SECONDS:
    return ""
```

Плюсы: простейший фильтр.
Минусы: не ловит длинную тишину (зажал на 5 секунд и молчал).

### C. Расширить BLANK_MARKERS + паттерны

Добавить известные паттерны галлюцинаций:

```python
BLANK_MARKERS = {
    "[BLANK_AUDIO]", "[ЗВУК]", "(silence)",
    "[Music]", "[Музыка]", "(music)",
}

HALLUCINATION_PATTERNS = [
    r"^(.{1,20})\1{2,}$",           # повтор короткой фразы 3+ раз
    r"(?i)thanks?\s+for\s+watch",    # "thanks for watching"
    r"(?i)подписывайтесь",           # "подписывайтесь на канал"
    r"(?i)субтитры",                 # "субтитры сделал..."
    r"(?i)subscribe",                # "subscribe"
]
```

Плюсы: ловит известные паттерны.
Минусы: всех не перечислишь, бесконечная гонка.

### D. Комбинированный подход (рекомендуется)

```
1. Проверить длину записи → < 0.5с → пропустить
2. Проверить RMS энергию → ниже порога → пропустить
3. Если whisper вернул текст → проверить BLANK_MARKERS + паттерны
4. Если подозрение на галлюцинацию → вернуть пустую строку
```

### E. Whisper VAD (--no-speech-thold)

whisper.cpp имеет встроенный параметр `--no-speech-thold` (порог тишины, дефолт 0.6):

```
whisper-cli ... --no-speech-thold 0.6
```

Можно попробовать повысить порог (например, 0.8) — whisper сам будет определять тишину и не галлюцинировать. Нужно проверить, есть ли этот параметр в нашей версии (v1.8.3).

## Приоритет

Средний — раздражающий UX-баг, но не ломает функционал.
