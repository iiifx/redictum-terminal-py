# FEATURE: Языко-зависимые промпты (prompt per language)

> Дата: 2026-02-20
> Статус: проектирование
> Связанный баг: `bug-2026-02-20-prompt-overrides-language.md`

## Проблема

Дефолтный prompt на английском перебивает `-l ru` на больших моделях (large-v3). Whisper воспринимает язык prompt как подсказку и выдаёт текст на английском вместо русского.

## Решение

Словарь `LANGUAGE_PROMPTS` в коде — дефолтные промпты для каждого языка. Выбор автоматический по `language` из конфига.

## Реализация

### Словарь промптов

```python
LANGUAGE_PROMPTS: dict[str, str] = {
    "en": (
        "Proper conversational speech with correct punctuation: "
        "commas, periods, question marks and exclamation marks. "
        "Anglicisms, technical terms and abbreviations are used."
    ),
    "ru": (
        "Правильная разговорная речь с корректной пунктуацией: "
        "запятые, точки, вопросительные и восклицательные знаки. "
        "Используются англицизмы, технические термины и сокращения."
    ),
    "uk": (
        "Правильне розмовне мовлення з коректною пунктуацією: "
        "коми, крапки, знаки питання та оклику. "
        "Використовуються англіцизми, технічні терміни та скорочення."
    ),
    "de": (
        "Korrekte Umgangssprache mit richtiger Zeichensetzung: "
        "Kommas, Punkte, Frage- und Ausrufezeichen. "
        "Anglizismen, Fachbegriffe und Abkürzungen werden verwendet."
    ),
    "fr": (
        "Discours conversationnel correct avec une ponctuation appropriée : "
        "virgules, points, points d'interrogation et d'exclamation. "
        "Anglicismes, termes techniques et abréviations sont utilisés."
    ),
    "es": (
        "Habla conversacional correcta con puntuación adecuada: "
        "comas, puntos, signos de interrogación y exclamación. "
        "Se utilizan anglicismos, términos técnicos y abreviaturas."
    ),
    "pt": (
        "Fala conversacional correta com pontuação adequada: "
        "vírgulas, pontos, pontos de interrogação e exclamação. "
        "São utilizados anglicismos, termos técnicos e abreviações."
    ),
    "it": (
        "Discorso colloquiale corretto con punteggiatura appropriata: "
        "virgole, punti, punti interrogativi e esclamativi. "
        "Vengono utilizzati anglicismi, termini tecnici e abbreviazioni."
    ),
    "zh": (
        "正确的对话语音，使用正确的标点符号："
        "逗号、句号、问号和感叹号。"
        "使用外来词、技术术语和缩写。"
    ),
    "ja": (
        "正しい会話音声、適切な句読点："
        "読点、句点、疑問符、感嘆符。"
        "外来語、専門用語、略語が使われます。"
    ),
    "ko": (
        "올바른 대화 음성, 정확한 구두점: "
        "쉼표, 마침표, 물음표, 느낌표. "
        "외래어, 기술 용어 및 약어가 사용됩니다."
    ),
    "pl": (
        "Poprawna mowa konwersacyjna z prawidłową interpunkcją: "
        "przecinki, kropki, znaki zapytania i wykrzykniki. "
        "Używane są anglicyzmy, terminy techniczne i skróty."
    ),
    "tr": (
        "Doğru noktalama işaretleriyle düzgün konuşma dili: "
        "virgüller, noktalar, soru ve ünlem işaretleri. "
        "Anglisizmler, teknik terimler ve kısaltmalar kullanılır."
    ),
}
```

### Логика выбора prompt в Transcriber

```python
def _resolve_prompt(self, language: str, user_prompt: str) -> str | None:
    """Pick the right prompt for transcription.

    Priority:
    1. User-defined prompt in config (non-empty) → use as-is
    2. Language found in LANGUAGE_PROMPTS → use matching prompt
    3. Language not in dict → no prompt (safe default)
    """
    if user_prompt:
        return user_prompt
    return LANGUAGE_PROMPTS.get(language)
```

### Изменения в transcribe()

```python
# Было:
if not translate and self._prompt:
    cmd.extend(["--prompt", self._prompt])

# Станет:
if not translate:
    prompt = self._resolve_prompt(self._language, self._prompt)
    if prompt:
        cmd.extend(["--prompt", prompt])
```

### Изменения в конфиге

Дефолтный `prompt` меняется с английского текста на пустую строку:

```python
# DEFAULT_CONFIG:
"prompt": "",  # auto-select by language from LANGUAGE_PROMPTS
```

```yaml
# config.yaml:
dependency:
  whisper:
    # Prompt для whisper: пустая строка = автовыбор по языку,
    # или впишите свой текст для override
    prompt: ""
```

### Обратная совместимость

Старые конфиги с английским prompt продолжат работать: поле непустое → override → используется как есть. Новые конфиги получат `prompt: ""` → авто-выбор по языку.
