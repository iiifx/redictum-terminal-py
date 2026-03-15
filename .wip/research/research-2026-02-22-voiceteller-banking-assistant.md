# RESEARCH: VoiceTeller — Banking Voice Assistant (distil-labs)

> Дата: 2026-02-22
> Статус: информационный, для будущего анализа
> URL: https://github.com/distil-labs/distil-voice-assistant-banking
> Лицензия: Apache 2.0

---

## Что это

Полностью локальный голосовой ассистент для банковских операций. Ключевая идея — замена облачных LLM тюненой моделью в 0.6B параметров, которая обходит 120B GPT по точности на узком домене (90.9% vs 87.5%).

## Стек

| Компонент | Модель | Латенси |
|-----------|--------|---------|
| ASR (речь → текст) | Qwen3-ASR-0.6B | ~200ms |
| SLM (интент + слоты) | Qwen3-0.6B (fine-tuned) | ~40ms |
| TTS (текст → речь) | Qwen3-TTS-12Hz-0.6B-Base | ~75ms |
| **Итого** | | **~315ms** |

Для сравнения: облачный LLM-пайплайн — 680-1300ms.

Инфраструктура: Python 3.12+, llama.cpp (llama-server), SoX, PyTorch, sounddevice.

---

## Архитектурные паттерны (полезные)

### 1. Protocol-based интерфейсы для ASR/TTS

```python
@runtime_checkable
class ASRModule(Protocol):
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str: ...

class TTSModule(Protocol):
    def synthesize(self, text: str) -> tuple[np.ndarray, int]: ...
```

- Структурная типизация — любой класс с нужным методом подходит, наследование не нужно
- `VoiceAssistant` принимает `asr: ASRModule`, а не `asr: Qwen3ASR` — полная развязка
- Подмена движка = передать другой объект, ноль изменений в pipeline

**Применимость для нас:** если когда-то захотим поддержать альтернативные ASR-движки (faster-whisper, Qwen3-ASR, Whisper Turbo), Protocol — чистый способ это сделать. Сейчас `Transcriber` привязан к `whisper-cli` subprocess.

### 2. Ленивый импорт тяжёлых зависимостей

```python
class Qwen3ASR:
    def __init__(self, model_path, device="auto"):
        import torch  # ← тяжёлый импорт только при создании объекта
        from qwen_asr import Qwen3ASRModel
        self.model = Qwen3ASRModel.from_pretrained(model_path, ...)
```

`import asr` — мгновенный. Загрузка модели — только при инстанциировании. У нас аналогичный подход уже применён (`pynput`, `rich`).

### 3. Data-driven оркестратор (таблицы вместо if/elif)

```python
FUNCTION_REQUIRED_ARGS = {
    "cancel_card": ["card_type", "card_last_four"],
    "transfer_money": ["amount", "from_account", "to_account"],
}
INDIVIDUAL_SLOT_PROMPTS = {
    "cancel_card": {"card_type": "credit or debit", "card_last_four": "the last 4 digits"},
}
SUCCESS_TEMPLATES = {
    "cancel_card": "Done. Your {card_type} card ending in {card_last_four} has been cancelled.",
}
```

Добавление нового интента = добавить строку в 3 словаря, ноль изменений в логике. Все бизнес-правила — данные, не код.

### 4. Stateless LLM-адаптер

`SLMClient` не хранит состояние диалога. Получает полную историю на каждый вызов, возвращает один function call. Состояние живёт в оркестраторе.

### 5. `tool_choice="required"` — ограничение выходного пространства

Модель **всегда** возвращает function call (14 функций × N слотов), никогда — свободный текст. Это позволяет 0.6B модели обходить 120B: выходное пространство крошечное, задача bounded.

**Ключевой инсайт:** ограничь выход модели до минимально необходимого формата, и маленькая специализированная модель справится лучше большой общей.

### 6. Pre-computation дорогих операций в `__init__`

```python
# Эмбеддинги голоса вычисляются один раз при старте, не на каждый вызов
self.voice_clone_prompt = self.model.create_voice_clone_prompt(
    ref_audio=ref_audio_path, ref_text=ref_text
)
```

Общий принцип: всё, что не зависит от per-call input, считать один раз в конструкторе.

---

## Архитектура pipeline

```
Microphone → [Qwen3-ASR] → text → [SLM: intent + slots] → [Orchestrator: шаблоны] → [Qwen3-TTS] → Speaker
                                          ↓
                                  JSON function call
                                  (не свободный текст!)
```

SLM определяет **интент** и **слоты**. Оркестратор:
- Проверяет, все ли слоты заполнены
- Если нет — генерит уточняющий вопрос из шаблона
- Если да — вызывает backend API, собирает ответ из шаблона
- SLM **никогда** не генерит текст пользователю (предсказуемо, без галлюцинаций)

Multi-turn slot filling: история диалога — `list[dict]` в OpenAI-формате. SLM видит весь контекст на каждом турне. Context window модели работает как state machine.

---

## Что НЕ применимо к нашему проекту

| Идея | Почему нет |
|------|-----------|
| Полный pipeline ASR→LLM→TTS | У нас утилита для транскрипции, не голосовой ассистент |
| Fine-tuning SLM | Нет задачи intent recognition |
| Push-to-talk через `input()` | У нас `pynput` hotkey с hold-delay — лучше |
| `sounddevice` для записи | У нас `arecord` subprocess — проще, нет зависимости от PortAudio |
| Voice cloning / TTS | Вне скоупа |
| Dependency flattening (`pip install --no-deps`) | Хрупко, у нас нет конфликтов зависимостей |

---

## Qwen3-ASR как альтернатива Whisper

- Модель: Qwen3-ASR-0.6B (630M параметров)
- Латенси: ~200ms (на GPU)
- Принимает любой sample rate (внутренний ресемплинг)
- Python-библиотека `qwen-asr`, не CLI subprocess
- Требует PyTorch + CUDA/MPS для приемлемой скорости

Для сравнения: whisper-cli large-v3 на нашей системе (CUDA 12.8, NVIDIA GPU) — тоже быстрый, но точные замеры не делали. Стоит сравнить, если будет задача на оптимизацию скорости ASR.

---

## Методология обучения (для справки)

- 77 hand-written seed-диалогов
- Синтетическое расширение через data augmentation
- Knowledge distillation: GPT-120B (teacher) → Qwen3-0.6B (student)
- Результат: student > teacher на узком домене
- ASR-aware: тренировочные данные содержат артефакты транскрипции (филлеры, омофоны, ошибки границ слов)
