#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки корректности кодировки в парсере
"""

import json
import sys
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

def test_encoding():
    """Проверка кодировки в сохранённых файлах"""

    print("Проверка кодировки парсера")
    print("=" * 50)

    # Проверяем тестовые файлы
    test_files = [
        'test_result.json',
        'yandex_test.json'
    ]

    for filename in test_files:
        filepath = Path(filename)

        if not filepath.exists():
            print(f"\n❌ Файл не найден: {filename}")
            continue

        print(f"\n✅ Проверка файла: {filename}")

        try:
            # Читаем файл с UTF-8
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Проверяем наличие русских символов
            title = data.get('title', '')

            print(f"  📄 Заголовок: {title[:100]}...")

            # Подсчитываем статистику
            has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in title)

            if has_cyrillic:
                print(f"  ✓ Кириллица обнаружена - кодировка работает правильно!")
            else:
                print(f"  ℹ️ Кириллица не найдена (это нормально для англоязычных сайтов)")

            print(f"  ℹ️ Ссылок: {len(data.get('links', []))}")
            print(f"  ℹ️ Изображений: {len(data.get('images', []))}")
            print(f"  ℹ️ Форм: {len(data.get('forms', []))}")

        except UnicodeDecodeError as e:
            print(f"  ❌ Ошибка кодировки: {e}")
        except json.JSONDecodeError as e:
            print(f"  ❌ Ошибка JSON: {e}")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

    print("\n" + "=" * 50)
    print("Проверка завершена!")

if __name__ == '__main__':
    test_encoding()
