# Bug: Command injection через bash -c в CUDA-установщике

**Приоритет:** HIGH
**Источник:** GitHub Copilot Security Audit (PR #1)

## Описание

В методе `WhisperInstaller._install_cuda()` (строка ~800) CUDA-пакеты устанавливаются через `bash -c` с подстановкой переменной в строку:

```python
install_script = (
    f"sudo dpkg -i {keyring_deb}"
    f" && sudo apt-get update -qq"
    f" && sudo apt-get install -y cuda-toolkit"
)
result = subprocess.run(["bash", "-c", install_script])
```

Хотя `keyring_deb` формируется из `tempfile.gettempdir()` + фиксированное имя (не пользовательский ввод), паттерн `bash -c` с f-string — плохая практика. Если в будущем путь станет динамическим или содержит спецсимволы shell — это станет реальной injection-уязвимостью.

Дополнительно: команда выполняется с `sudo`, что усиливает потенциальный ущерб.

## Решение

Заменить `bash -c` на 3 отдельных вызова `subprocess.run()` с list-аргументами:

```python
# Step 1: Install keyring
result = subprocess.run(["sudo", "dpkg", "-i", str(keyring_deb)])
if result.returncode != 0:
    return False

# Step 2: Update package list
result = subprocess.run(["sudo", "apt-get", "update", "-qq"])
if result.returncode != 0:
    return False

# Step 3: Install CUDA toolkit
result = subprocess.run(["sudo", "apt-get", "install", "-y", "cuda-toolkit"])
```

Бонус: каждый шаг рапортует об ошибке отдельно — проще диагностировать.
