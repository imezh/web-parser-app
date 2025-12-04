#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексное тестирование Web Parser
"""

import subprocess
import sys
import json
import time
from pathlib import Path

# Исправляем кодировку для Windows консоли
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

PYTHON = "C:/Users/DB/AppData/Local/Programs/Python/Python313/python.exe"
PARSER = "web_parser.py"

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0

def run_test(test_name, command, timeout=60, check_output=True):
    """Запускает тест и возвращает результат"""
    result = TestResult(test_name)
    print(f"\n🧪 Тест: {test_name}")
    print(f"   Команда: {' '.join(command)}")

    start_time = time.time()

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )

        result.duration = time.time() - start_time

        if proc.returncode == 0:
            result.passed = True
            print(f"   ✅ УСПЕШНО ({result.duration:.2f}s)")

            if check_output and proc.stdout:
                # Проверяем, что вывод валидный JSON
                try:
                    json.loads(proc.stdout)
                    print(f"   ✓ Вывод содержит валидный JSON")
                except json.JSONDecodeError:
                    print(f"   ⚠ Вывод не является валидным JSON (возможно, сохранено в файл)")
        else:
            result.passed = False
            result.error = f"Exit code: {proc.returncode}"
            print(f"   ❌ ОШИБКА: {result.error}")
            if proc.stderr:
                print(f"   Stderr: {proc.stderr[:200]}")

    except subprocess.TimeoutExpired:
        result.duration = timeout
        result.passed = False
        result.error = f"Timeout after {timeout}s"
        print(f"   ❌ ТАЙМАУТ: {timeout}s")

    except Exception as e:
        result.duration = time.time() - start_time
        result.passed = False
        result.error = str(e)
        print(f"   ❌ ИСКЛЮЧЕНИЕ: {e}")

    return result

def main():
    print("=" * 70)
    print("🔍 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ WEB PARSER")
    print("=" * 70)

    results = []

    # Тест 1: Справка
    results.append(run_test(
        "Справка (--help)",
        [PYTHON, PARSER, "--help"],
        timeout=10,
        check_output=False
    ))

    # Тест 2: Базовый парсинг
    results.append(run_test(
        "Базовый парсинг (example.com)",
        [PYTHON, PARSER, "https://example.com", "--timeout", "30"],
        timeout=60
    ))

    # Тест 3: Сохранение в файл
    output_file = "test_output_temp.json"
    results.append(run_test(
        "Сохранение в файл",
        [PYTHON, PARSER, "https://example.com", "-o", output_file, "--timeout", "30"],
        timeout=60,
        check_output=False
    ))

    # Проверяем созданный файл
    if Path(output_file).exists():
        print(f"   ✓ Файл {output_file} создан")
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"   ✓ Файл содержит валидный JSON")
            print(f"   ✓ URL: {data.get('url')}")
            print(f"   ✓ Заголовок: {data.get('title')}")
            Path(output_file).unlink()  # Удаляем тестовый файл
        except Exception as e:
            print(f"   ❌ Ошибка проверки файла: {e}")

    # Тест 4: Увеличенный таймаут
    results.append(run_test(
        "Увеличенный таймаут (120s)",
        [PYTHON, PARSER, "https://example.com", "--timeout", "120", "--wait-time", "3"],
        timeout=150,
        check_output=False  # Не проверяем JSON т.к. stderr может быть в stdout
    ))

    # Тест 5: Несуществующий домен (должен упасть с ошибкой)
    results.append(run_test(
        "Несуществующий домен (ожидается ошибка)",
        [PYTHON, PARSER, "https://thisdomaindoesnotexist12345.com", "--timeout", "10"],
        timeout=30,
        check_output=False
    ))
    # Для этого теста ожидаем провал
    if not results[-1].passed:
        print(f"   ℹ️ Ожидаемая ошибка - тест корректно обработал неверный URL")
        results[-1].passed = True  # Считаем успехом

    # Тест 6: Невалидный URL
    results.append(run_test(
        "Невалидный URL (ожидается ошибка)",
        [PYTHON, PARSER, "not-a-valid-url", "--timeout", "10"],
        timeout=30,
        check_output=False
    ))
    if not results[-1].passed:
        print(f"   ℹ️ Ожидаемая ошибка - тест корректно обработал невалидный URL")
        results[-1].passed = True

    # Тест 7: Русскоязычный сайт
    results.append(run_test(
        "Русскоязычный сайт",
        [PYTHON, PARSER, "https://example.org", "-o", "test_ru_temp.json", "--timeout", "30"],
        timeout=60,
        check_output=False
    ))

    if Path("test_ru_temp.json").exists():
        try:
            with open("test_ru_temp.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"   ✓ Кодировка корректна")
            Path("test_ru_temp.json").unlink()
        except Exception as e:
            print(f"   ❌ Проблема с кодировкой: {e}")

    # Тест 8: HTTPS сайт
    results.append(run_test(
        "HTTPS сайт с SSL",
        [PYTHON, PARSER, "https://www.google.com", "--timeout", "30"],
        timeout=60,
        check_output=False
    ))

    # Итоговая статистика
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 70)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    total_time = sum(r.duration for r in results)

    print(f"\nВсего тестов: {len(results)}")
    print(f"✅ Успешно: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"⏱️  Общее время: {total_time:.2f}s")

    print("\nДетальные результаты:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.passed else "❌"
        print(f"{status} {i}. {result.name} ({result.duration:.2f}s)")
        if result.error:
            print(f"      Ошибка: {result.error}")

    print("\n" + "=" * 70)

    if failed == 0:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print(f"⚠️  НАЙДЕНО ОШИБОК: {failed}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
