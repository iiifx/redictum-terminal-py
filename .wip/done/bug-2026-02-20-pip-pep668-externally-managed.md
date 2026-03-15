# BUG: pip install заблокирован на новых системах (PEP 668)

> Дата: 2026-02-20
> Источник: репорт от тестировщика
> Статус: анализ

## Ошибка

```
error: externally-managed-environment
× This environment is externally managed
╰─> To install Python packages system-wide, try apt install python3-xyz
```

## Причина

PEP 668 (Python 3.11+). Начиная с Ubuntu 23.04 / Debian 12 / Linux Mint 22, системный Python запрещает `pip install` без venv. Файл-маркер `/usr/lib/python3.*/EXTERNALLY-MANAGED` блокирует pip.

Наш скрипт (строка 529):
```python
cmd = ["pip", "install", *packages]
```
Просто вызывает `pip install` — на новых системах гарантированный отказ.

## Затронутые системы

- Ubuntu 23.04+
- Debian 12+
- Linux Mint 22+
- Fedora 38+
- Любой дистрибутив с Python 3.11+ и маркером EXTERNALLY-MANAGED

## Варианты решения

### A. Приоритет apt-пакетам

Все наши pip-зависимости есть как системные пакеты:
- `pynput` → `python3-pynput` (apt)
- `PyYAML` → `python3-yaml` (apt)
- `rich` → `python3-rich` (apt)

Логика:
1. Сначала пробуем `apt install python3-pynput python3-yaml` (вместе с другими apt-пакетами)
2. Если apt-пакет недоступен — fallback на pip
3. Если pip заблокирован — fallback на `pip install --user`

Плюсы: нет конфликтов с системой, один `sudo apt install` на всё.
Минусы: версии в apt могут быть старые.

### B. Автоматический venv

```python
VENV_DIR = SCRIPT_DIR / ".venv"

def _ensure_venv(self) -> None:
    if not VENV_DIR.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)])
    pip = VENV_DIR / "bin" / "pip"
    subprocess.run([str(pip), "install", *packages])

def _reexec_in_venv(self) -> None:
    venv_python = VENV_DIR / "bin" / "python3"
    os.execv(str(venv_python), [str(venv_python), *sys.argv])
```

Плюсы: полная изоляция, любая версия пакетов.
Минусы: сложнее, ещё один шаг при установке, ~50 MB на диске.

### C. pip install --user (fallback)

```python
def _install_pip(self, packages: list[str]) -> bool:
    cmd = ["pip", "install", *packages]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True
    if "externally-managed" in result.stderr.lower():
        cmd = ["pip", "install", "--user", *packages]
        result = subprocess.run(cmd)
        return result.returncode == 0
    return False
```

Плюсы: минимальные изменения.
Минусы: `--user` тоже может не работать на некоторых системах.

### D. Комбинированная стратегия (рекомендуется)

```
1. Проверяем import → если есть, ничего не делаем
2. Пробуем apt install python3-pynput python3-yaml → если ОК, готово
3. Пробуем pip install → если ОК, готово
4. Пробуем pip install --user → если ОК, готово
5. Если всё сломалось → понятная инструкция для ручной установки
```

### Маппинг pip → apt

```python
PIP_TO_APT: dict[str, str] = {
    "pynput": "python3-pynput",
    "PyYAML": "python3-yaml",
    "rich": "python3-rich",
}
```

## Приоритет

Высокий — затрагивает все новые дистрибутивы Linux.
