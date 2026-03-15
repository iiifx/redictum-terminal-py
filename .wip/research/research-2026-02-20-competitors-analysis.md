# RESEARCH: Анализ конкурентов — voice-to-text для Linux

> Дата: 2026-02-20 (обновлено 2026-03-15)
> Статус: информационный, для будущего анализа

---

## Прямые аналоги (push-to-talk + whisper.cpp + Linux)

### ⭐ Handy — главный конкурент (добавлено 2026-03-15)
- **URL:** https://github.com/cjpais/Handy | https://handy.computer
- **Язык:** Rust + Tauri v2 (React/TypeScript фронт)
- **Stars:** 17,657 | **Forks:** 1,347 | **Issues:** 97 open
- **Лицензия:** MIT
- **Создан:** Февраль 2025, **активно развивается** (последний пуш: 2026-03-15)
- **Установка:** `brew install --cask handy` (macOS), `winget install cjpais.Handy` (Windows), .deb/.rpm (Linux)
- **Кроссплатформа:** macOS (Intel/Apple Silicon), Windows (x64), Linux (x64)
- **Фишки:**
  - Whisper модели (Small/Medium/Turbo/Large) с GPU-ускорением
  - **Parakeet V3** — CPU-only альтернатива Whisper, авто-определение языка, ~5x realtime на mid-range CPU
  - **Silero VAD** — фильтрация тишины ДО транскрипции (экономит время модели)
  - Push-to-talk с настраиваемыми hotkeys, автовставка в активное поле
  - Wayland support (wtype / dotool)
  - Кастомные GGML-модели — автообнаружение в папке models
  - CLI remote control: `--toggle-transcription`, `--cancel`, `--start-hidden`
  - GUI с system tray, настройки через интерфейс
  - Автоскачивание моделей при первом запуске
- **Нет:** daemon mode, автоустановки системных зависимостей, translate mode, clipboard save/restore, audio normalization, звуковых уведомлений, ротации файлов, конфига с комментариями
- **Проблемы:** Whisper crashes на Windows/Linux (configuration-dependent), на Linux overlay может красть фокус, нужен `libgtk-layer-shell`
- **Вердикт:** самый серьёзный конкурент по масштабу (17K+ звёзд, кроссплатформа, активное развитие). Целится в массовый десктоп (GUI + пакетные менеджеры). Мы — CLI power-tool для Linux. Разные ниши, но большое пересечение.

### Voxtype
- **URL:** https://voxtype.io/ | https://github.com/peteonrails/voxtype
- **Язык:** Rust, один бинарник
- **Установка:** скачать бинарник, без зависимостей
- **Фишки:**
  - Vulkan / CUDA / Metal / ROCm GPU-ускорение
  - Wayland-first (wtype), fallback на ydotool и clipboard
  - Поддержка NVIDIA Parakeet модели (альтернатива Whisper, быстрее на некоторых GPU)
  - Sub-second транскрипция на large-v3-turbo с GPU
  - Полная Unicode/CJK поддержка
  - Выбор hotkey, модели, output mode через конфиг
- **Нет:** daemon mode, автоустановки зависимостей, translate mode

### BlahST — набор утилит для power users
- **URL:** https://github.com/QuantiusBenignus/BlahST
- **Язык:** Bash-скрипты
- **Фишки:**
  - Сетевая транскрипция (whisper.cpp server по LAN, API-вызовы)
  - Интеграция с llama.cpp — голосовой чат с локальным LLM
  - Piper TTS — ответ голосом
  - Streaming speech-to-speech (blahstream)
  - 90x realtime на AMD64 + 12GB VRAM
- **Нет:** единого скрипта, автоустановки, GUI

### OpenWhispr — десктоп-приложение с bundled бинарниками
- **URL:** https://github.com/OpenWhispr/openwhispr | https://openwhispr.com/
- **Язык:** Electron
- **Фишки:**
  - Bundled whisper.cpp бинарники — не нужен cmake/build-essential
  - NVIDIA Parakeet модели
  - Авто-выбор метода вставки: wtype → ydotool → xdotool → clipboard
  - Кроссплатформа (Windows, macOS, Linux)
  - BYOK (Bring Your Own Key) для облачных моделей
- **Нет:** daemon mode, CLI, один файл

### whisper-dictation — NixOS-ориентированный
- **URL:** https://github.com/jacopone/whisper-dictation
- **Язык:** Python
- **Фишки:**
  - Daemon mode (`python -m whisper_dictation.daemon`)
  - Real-time feedback во время записи
  - Push-to-talk с hotkey
  - Privacy-first, 100% локально
- **Нет:** автоустановки, широкой дистрибутивной совместимости

---

## GUI-решения

### Dictator — PyQt6 floating interface
- **URL:** https://github.com/chris17453/dictator | PyPI: `the-dictator`
- **Язык:** Python, PyQt6
- **Stars:** 4, **Commits:** 3 (!)
- **Создан:** Сентябрь 2025, последнее обновление: Январь 2026
- **Whisper:** faster-whisper (Python), **CPU only** (hardcoded `device="cpu"`)
- **Модель:** tiny по дефолту
- **Фишки:**
  - Плавающее always-on-top окно с real-time визуализацией звука
  - System tray, сессии, история транскрипций
  - Выбор микрофона (`--list-devices` / `--set-device`)
  - GNOME интеграция (`.desktop`, иконки)
  - Ctrl+Space hotkey
- **Проблемы:**
  - CPU only — нет GPU-ускорения вообще
  - 12+ Python-зависимостей (PyQt6, numpy, librosa, PyAudio, sounddevice, pynput...)
  - `ssl._create_default_https_context = ssl._create_unverified_context` — глобальный SSL bypass (security hole)
  - 3 коммита за всю историю, второй называется "massive"
  - PR #2 (открыт) фиксит базовые баги: `python` vs `sys.executable`, clipboard не работал без фокуса окна
  - Нет нормализации, нет детекции тишины, нет ротации файлов, нет translate mode
- **Вердикт:** ранний прототип с красивым README. Не конкурент по функционалу.

### Turbo-Whisper — SuperWhisper для Linux
- **URL:** https://github.com/knowall-ai/turbo-whisper
- GUI с waveform визуализацией, 99 языков, красивый интерфейс

### Whispering — кроссплатформенное Svelte-приложение
- **URL:** https://news.ycombinator.com/item?id=44942731
- Desktop + browser, цепочки AI-обработки текста (форматирование, cleanup), MIT
- Локальные модели (Speaches) + облачные (OpenAI, Groq, ElevenLabs)

### Whis — Flatpak
- **URL:** https://flathub.org/en/apps/ink.whis.Whis
- Установка одной командой через Flathub, облако или локально

### Amical — AI dictation + заметки
- **URL:** https://github.com/amicalhq/amical
- Open source, local-first, Whisper + open source LLM, офлайн

---

## Альтернативный движок (не whisper.cpp)

### Nerd-Dictation — VOSK API
- **URL:** https://github.com/ideasman42/nerd-dictation
- **Язык:** Python, один файл
- **Фишки:**
  - VOSK API (легче whisper, меньше ресурсов)
  - Конвертация чисел в цифры ("three million" → 3,000,000)
  - Hackable Python-пайплайн для манипуляции текстом
  - Много языковых моделей (украинский, русский, китайский и т.д.)
- **Нет:** whisper-качества распознавания, GPU-ускорения

### SoupaWhisper — faster-whisper
- **URL:** https://www.ksred.com/soupawhisper-how-i-replaced-superwhisper-on-linux/
- Python, faster-whisper bindings (не whisper.cpp), F12 hotkey

---

## Сравнительная таблица: что есть у конкурентов, чего нет у нас

| Фича | Кто имеет | У Redictum |
|---|---|---|
| Wayland support (wtype, wl-clipboard) | **Handy**, Voxtype, OpenWhispr | Нет (X11 only) |
| Кроссплатформа (Win/Mac/Linux) | **Handy**, OpenWhispr | Только Linux |
| Silero VAD (фильтрация тишины до транскрипции) | **Handy** | Только post-hoc через ffmpeg |
| Пакетные менеджеры (brew, winget, deb/rpm) | **Handy** | curl + chmod +x |
| Pre-built whisper бинарники | **Handy**, OpenWhispr | Нет (сборка cmake) |
| Альтернативные модели (Parakeet, VOSK) | **Handy**, Voxtype, OpenWhispr, Nerd-Dictation | Нет |
| GUI с system tray и настройками | **Handy**, Turbo-Whisper, Dictator | Нет (CLI only) |
| Кастомные GGML-модели (автообнаружение) | **Handy** | Нет |
| LLM-обработка текста после транскрипции | BlahST, Whispering, Amical | Нет |
| Сетевая транскрипция (whisper server по LAN) | BlahST | Нет |
| Streaming speech-to-text | BlahST (blahstream) | Нет |
| Числа → цифры ("three" → "3") | Nerd-Dictation | Нет |
| Rust / один бинарник без зависимостей | Voxtype | Python + pip deps |
| Vulkan GPU backend | Voxtype | Нет (только CUDA) |
| Цепочки AI-обработки (cleanup, formatting) | Whispering | Нет |
| Авто-выбор метода вставки (wtype→ydotool→xdotool) | OpenWhispr | Только xdotool |
| Flatpak/Snap пакет | Whis | Нет |

## Сравнительная таблица: что есть у нас, чего нет/редко у конкурентов

| Фича | Redictum | Конкуренты |
|---|---|---|
| Полная автоустановка (apt + pip + whisper + CUDA + модель) | Да | Почти никто |
| Один файл, установка через curl | Да | Нет |
| Daemon mode (start/stop/status, double fork) | Да | whisper-dictation (частично) |
| Clipboard save/restore (текст + изображения + binary) | Да | OpenWhispr (только текст) |
| Звуковые уведомления (генерация WAV тонов в коде) | Да | Редко |
| Автосборка whisper.cpp с CUDA detection + toolkit install | Да | Нет |
| Translate mode (Ctrl+Insert → английский) | Да | Редко |
| YAML конфиг с комментариями | Да | Редко |
| Audio normalization (ffmpeg loudnorm) | Да | Нет |
| Ротация файлов (аудио + транскрипты) | Да | Нет |

---

## Потенциальные идеи из конкурентов (для обдумывания)

1. **Silero VAD** (из Handy) — фильтрация тишины ДО транскрипции. Экономит время модели, улучшает качество. У нас сейчас только post-hoc speech detection через ffmpeg.
2. **Parakeet V3** (из Handy) — CPU-only модель с авто-определением языка, ~5x realtime. Альтернатива Whisper для машин без GPU.
3. **Wayland** — Handy, Voxtype и OpenWhispr уже поддерживают. Растущая доля рынка.
4. **Pre-built бинарники** — Handy и OpenWhispr bundlят whisper. Убирает cmake/build-essential.
5. **Авто-выбор метода вставки** — OpenWhispr пробует wtype → ydotool → xdotool → clipboard. Устойчивее.
6. **LLM post-processing** — BlahST и Whispering отправляют текст в LLM для форматирования/cleanup.
7. **Сетевая транскрипция** — BlahST может использовать whisper.cpp server на другой машине.
8. **Числа → цифры** — Nerd-Dictation конвертирует "twenty three" → 23. Полезно.
9. **Vulkan backend** — Voxtype поддерживает Vulkan для AMD GPU. У нас только CUDA (NVIDIA).

---

## Выводы и рекомендации

### Топ приоритет — must have

**1. Silero VAD — фильтрация тишины до транскрипции (из Handy)**
Handy фильтрует тишину через Silero VAD ДО отправки в модель. У нас — только post-hoc детекция через ffmpeg (после записи). VAD до транскрипции = быстрее + точнее. Для Python есть `silero-vad` (PyTorch) или лёгкий `webrtcvad` (C, без PyTorch). Реализация — обёртка вокруг записанного аудио перед Whisper.

**2. Авто-выбор метода вставки (из OpenWhispr)**
Сейчас жёстко `xdotool` → `Ctrl+V`. OpenWhispr пробует цепочку: `wtype` → `ydotool` → `xdotool` → `clipboard`. Убивает двух зайцев: Wayland-совместимость + устойчивость на X11. Реализация простая — try/except по цепочке. Подготовка к Wayland без полного переписывания.

**3. LLM пост-обработка (из BlahST / Whispering)**
Killer feature. Отправить текст после whisper в локальный LLM (llama.cpp, ollama) для: форматирования, удаления whisper-мусора ("ммм", "эээ", "субтитры от..."), конвертации чисел, стилизации. Один LLM-шаг заменяет несколько отдельных фич. Optional — не у всех есть LLM локально.

### Средний приоритет — nice to have

**4. Parakeet V3 как альтернативный движок (из Handy)**
CPU-only модель, авто-определение языка, ~5x realtime на mid-range CPU. Для пользователей без GPU — реальная альтернатива Whisper. Требует другой backend (не whisper-cli subprocess). Наша backend-архитектура (ABC TranscriberBackend) уже готова для этого.

**5. Wayland поддержка (из Handy / Voxtype)**
Ubuntu 24.04 уже Wayland по дефолту. Handy поддерживает через wtype/dotool. Но `pynput` и `xclip` — X11. Переход нетривиальный. Начать с авто-выбора вставки (п.2), полный Wayland — отдельная итерация.

**6. Pre-built whisper бинарники (из Handy / OpenWhispr)**
Сборка whisper.cpp через cmake — самый болезненный этап (10-15 мин с CUDA). Handy и OpenWhispr bundlят бинарники. Хостить pre-built `whisper-cli` на GitHub Releases для CPU и CUDA. Инфраструктурная задача — CI, несколько платформ, версионирование.

**7. Числа → цифры (из Nerd-Dictation)**
"двадцать три" → "23", "три миллиона" → "3 000 000". Пост-процессор regex-заменами. Может быть заменён LLM пост-обработкой (п.3).

**8. Сетевая транскрипция (из BlahST)**
whisper.cpp server на мощной машине, лёгкий клиент на ноутбуке. Для офисных сетапов — золото. Узкая аудитория.

### Низкий приоритет

**9. Vulkan GPU backend** — для AMD. whisper.cpp Vulkan ещё сырой.

**10. GUI с waveform** — мы CLI-first, это наша фишка. GUI = другой продукт.

### Матрица impact/effort

| Фича | Impact | Effort | Приоритет |
|---|---|---|---|
| Silero VAD (фильтрация тишины) | Высокий | Средний | Первым делом |
| Авто-выбор метода вставки | Высокий | Низкий | Первым делом |
| LLM пост-обработка | Высокий | Средний | Следующий шаг |
| Parakeet V3 (CPU-only движок) | Средний | Средний | После backend refactor |
| Pre-built бинарники | Высокий | Высокий | Инфраструктура |
| Wayland (полный) | Высокий | Высокий | Стратегически |

---

*Этот документ — исключительно для анализа. Решения о внедрении принимаются отдельно.*
