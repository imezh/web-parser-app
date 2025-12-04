#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Parser Application
Парсит веб-страницы с поддержкой сертификатов и ожидания загрузки
"""

import sys
import json
import argparse
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import subprocess

# Настройка логгера
logger = logging.getLogger('web_parser')


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """
    Настройка системы логирования

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу для сохранения логов (опционально)
    """
    # Очищаем существующие handlers
    logger.handlers.clear()

    # Устанавливаем уровень
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Форматирование логов
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Консольный handler (только INFO и выше, если не DEBUG режим)
    console_handler = logging.StreamHandler(sys.stderr)
    if numeric_level == logging.DEBUG:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый handler с ротацией (если указан файл)
    if log_file:
        try:
            # Создаем директорию для логов если нужно
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Ротация: макс 10MB, 5 файлов
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # В файл пишем все
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            logger.info(f"Логирование в файл: {log_file}")
        except Exception as e:
            logger.warning(f"Не удалось настроить файловое логирование: {e}")

    logger.debug(f"Логирование настроено: уровень={log_level}")


class WebParser:
    """Класс для парсинга веб-страниц"""

    def __init__(self, headless: bool = True, timeout: int = 60000):
        """
        Инициализация парсера

        Args:
            headless: Запуск браузера в фоновом режиме
            timeout: Таймаут загрузки страницы в миллисекундах
        """
        logger.debug(f"Инициализация WebParser: headless={headless}, timeout={timeout}ms")
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        logger.debug("WebParser инициализирован успешно")

    def get_windows_certificates(self) -> list:
        """
        Получает список сертификатов из хранилища Windows

        Returns:
            Список путей к сертификатам
        """
        logger.info("Поиск сертификатов в хранилище Windows")
        try:
            # Используем PowerShell для получения сертификатов из Personal Store
            powershell_cmd = """
            Get-ChildItem -Path Cert:\\CurrentUser\\My |
            Where-Object { $_.HasPrivateKey -eq $true } |
            Select-Object -First 1 -ExpandProperty Thumbprint
            """
            logger.debug("Выполнение PowerShell команды для получения сертификатов")
            result = subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                certs = [result.stdout.strip()]
                logger.info(f"Найдено сертификатов: {len(certs)}")
                logger.debug(f"Сертификаты: {certs}")
                return certs
            else:
                logger.warning("Сертификаты с приватным ключом не найдены")
                return []
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при получении сертификатов из PowerShell")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении сертификатов: {e}", exc_info=True)
            return []

    def setup_browser(self, ignore_https_errors: bool = False):
        """
        Настройка и запуск браузера

        Args:
            ignore_https_errors: Игнорировать ошибки SSL
        """
        logger.info("Запуск браузера Chromium")
        logger.debug(f"Параметры: headless={self.headless}, ignore_https_errors={ignore_https_errors}")

        try:
            logger.debug("Инициализация Playwright")
            self.playwright = sync_playwright().start()

            # Запускаем Chromium с поддержкой клиентских сертификатов
            browser_args = [
                '--ignore-certificate-errors',
                '--disable-web-security',
                '--auto-select-client-certificate',
            ]
            logger.debug(f"Аргументы браузера: {browser_args}")

            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            logger.info("Браузер Chromium запущен успешно")

            # Создаем контекст с настройками
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            logger.debug(f"User-Agent: {user_agent}")

            self.context = self.browser.new_context(
                ignore_https_errors=ignore_https_errors,
                accept_downloads=True,
                java_script_enabled=True,
                user_agent=user_agent
            )
            logger.debug("Контекст браузера создан")

            self.page = self.context.new_page()
            logger.debug("Новая страница создана")

            # Устанавливаем таймаут
            self.page.set_default_timeout(self.timeout)
            self.page.set_default_navigation_timeout(self.timeout)
            logger.debug(f"Таймауты установлены: {self.timeout}ms")

        except Exception as e:
            logger.error(f"Ошибка при настройке браузера: {e}", exc_info=True)
            raise

    def wait_for_page_load(self, additional_wait: int = 2):
        """
        Ожидание полной загрузки страницы

        Args:
            additional_wait: Дополнительное время ожидания после события load (секунды)
        """
        logger.info("Ожидание загрузки страницы")
        if not self.page:
            logger.error("Попытка ожидания загрузки без инициализированной страницы")
            raise RuntimeError("Страница не инициализирована")

        try:
            # Ждем загрузки DOM
            logger.debug("Ожидание domcontentloaded")
            self.page.wait_for_load_state('domcontentloaded')
            logger.debug("DOM загружен")

            # Ждем полной загрузки всех ресурсов
            logger.debug("Ожидание load")
            self.page.wait_for_load_state('load')
            logger.debug("Все ресурсы загружены")

            # Ждем завершения всех сетевых запросов
            logger.debug("Ожидание networkidle")
            self.page.wait_for_load_state('networkidle', timeout=self.timeout)
            logger.debug("Сетевые запросы завершены")

            # Дополнительное ожидание для динамического контента
            if additional_wait > 0:
                logger.debug(f"Дополнительное ожидание: {additional_wait}s")
                time.sleep(additional_wait)

            logger.info("Страница полностью загружена")
            print(f"✓ Страница полностью загружена", file=sys.stderr)

        except Exception as e:
            logger.error(f"Ошибка при ожидании загрузки страницы: {e}", exc_info=True)
            raise

    def parse_page(self, url: str, wait_selector: Optional[str] = None) -> Dict[str, Any]:
        """
        Парсинг веб-страницы

        Args:
            url: URL страницы для парсинга
            wait_selector: CSS селектор элемента, который нужно дождаться

        Returns:
            Словарь с данными страницы
        """
        logger.info(f"Начало парсинга: {url}")
        if not self.page:
            logger.error("Попытка парсинга без инициализированного браузера")
            raise RuntimeError("Браузер не инициализирован")

        print(f"Загрузка страницы: {url}", file=sys.stderr)

        try:
            # Переходим на страницу
            logger.debug(f"Переход на URL: {url}")
            start_time = time.time()
            response = self.page.goto(url, wait_until='commit')
            nav_time = time.time() - start_time

            if response:
                logger.info(f"Страница загружена, статус: {response.status}, время: {nav_time:.2f}s")
            else:
                logger.warning("Response не получен")

            # Ожидание загрузки
            self.wait_for_page_load()

            # Если указан селектор, ждем его появления
            if wait_selector:
                logger.info(f"Ожидание селектора: {wait_selector}")
                print(f"Ожидание элемента: {wait_selector}", file=sys.stderr)
                self.page.wait_for_selector(wait_selector, timeout=self.timeout)
                logger.debug(f"Селектор {wait_selector} найден")

        except Exception as e:
            logger.error(f"Ошибка при навигации на страницу: {e}", exc_info=True)
            raise

        # Собираем данные
        result = {
            'url': self.page.url,
            'title': self.page.title(),
            'status_code': response.status if response else None,
            'html': self.page.content(),
            'text': self.page.inner_text('body'),
            'metadata': {
                'viewport': self.page.viewport_size,
                'cookies': self.context.cookies(),
            },
            'links': [],
            'forms': [],
            'images': [],
        }

        # Извлекаем ссылки
        logger.debug("Извлечение ссылок")
        try:
            links = self.page.eval_on_selector_all(
                'a[href]',
                '(elements) => elements.map(e => ({href: e.href, text: e.textContent.trim()}))'
            )
            result['links'] = links
            logger.info(f"Извлечено ссылок: {len(links)}")
        except Exception as e:
            logger.warning(f"Не удалось извлечь ссылки: {e}")
            print(f"Предупреждение: Не удалось извлечь ссылки: {e}", file=sys.stderr)

        # Извлекаем информацию о формах
        logger.debug("Извлечение форм")
        try:
            forms = self.page.eval_on_selector_all(
                'form',
                '''(elements) => elements.map(form => ({
                    action: form.action,
                    method: form.method,
                    fields: Array.from(form.elements).map(el => ({
                        name: el.name,
                        type: el.type,
                        tag: el.tagName
                    }))
                }))'''
            )
            result['forms'] = forms
            logger.info(f"Извлечено форм: {len(forms)}")
        except Exception as e:
            logger.warning(f"Не удалось извлечь формы: {e}")
            print(f"Предупреждение: Не удалось извлечь формы: {e}", file=sys.stderr)

        # Извлекаем изображения
        logger.debug("Извлечение изображений")
        try:
            images = self.page.eval_on_selector_all(
                'img[src]',
                '(elements) => elements.map(img => ({src: img.src, alt: img.alt}))'
            )
            result['images'] = images
            logger.info(f"Извлечено изображений: {len(images)}")
        except Exception as e:
            logger.warning(f"Не удалось извлечь изображения: {e}")
            print(f"Предупреждение: Не удалось извлечь изображения: {e}", file=sys.stderr)

        logger.info(f"Парсинг завершен успешно: заголовок='{result['title']}', "
                   f"ссылок={len(result['links'])}, форм={len(result['forms'])}, "
                   f"изображений={len(result['images'])}")
        print(f"✓ Парсинг завершен успешно", file=sys.stderr)

        return result

    def close(self):
        """Закрытие браузера и освобождение ресурсов"""
        logger.info("Закрытие браузера и освобождение ресурсов")

        try:
            if self.page:
                logger.debug("Закрытие страницы")
                self.page.close()
                logger.debug("Страница закрыта")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии страницы: {e}")
            print(f"Предупреждение: Ошибка при закрытии страницы: {e}", file=sys.stderr)

        try:
            if self.context:
                logger.debug("Закрытие контекста")
                self.context.close()
                logger.debug("Контекст закрыт")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии контекста: {e}")
            print(f"Предупреждение: Ошибка при закрытии контекста: {e}", file=sys.stderr)

        try:
            if self.browser:
                logger.debug("Закрытие браузера")
                self.browser.close()
                logger.debug("Браузер закрыт")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии браузера: {e}")
            print(f"Предупреждение: Ошибка при закрытии браузера: {e}", file=sys.stderr)

        try:
            if self.playwright:
                logger.debug("Остановка Playwright")
                self.playwright.stop()
                logger.debug("Playwright остановлен")
        except Exception as e:
            logger.warning(f"Ошибка при остановке Playwright: {e}")
            print(f"Предупреждение: Ошибка при остановке Playwright: {e}", file=sys.stderr)

        logger.info("Все ресурсы освобождены")


def main():
    """Основная функция приложения"""
    # Исправляем кодировку для Windows консоли
    if sys.platform == 'win32':
        try:
            # Устанавливаем UTF-8 для stdout и stderr
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            # Для старых версий Python
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    parser = argparse.ArgumentParser(
        description='Web Parser - парсинг веб-страниц с поддержкой сертификатов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s https://example.com
  %(prog)s https://example.com -o result.json
  %(prog)s https://example.com --wait-selector "#content"
  %(prog)s https://example.com --visible --timeout 120
        """
    )

    parser.add_argument(
        'url',
        help='URL страницы для парсинга'
    )

    parser.add_argument(
        '-o', '--output',
        help='Путь к файлу для сохранения результата (по умолчанию: вывод в консоль)',
        default=None
    )

    parser.add_argument(
        '--wait-selector',
        help='CSS селектор элемента, который нужно дождаться',
        default=None
    )

    parser.add_argument(
        '--timeout',
        help='Таймаут загрузки страницы в секундах (по умолчанию: 60)',
        type=int,
        default=60
    )

    parser.add_argument(
        '--visible',
        help='Показывать окно браузера (для отладки)',
        action='store_true'
    )

    parser.add_argument(
        '--ignore-https-errors',
        help='Игнорировать ошибки SSL сертификатов',
        action='store_true'
    )

    parser.add_argument(
        '--wait-time',
        help='Дополнительное время ожидания после загрузки в секундах (по умолчанию: 2)',
        type=int,
        default=2
    )

    parser.add_argument(
        '--log-level',
        help='Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO'
    )

    parser.add_argument(
        '--log-file',
        help='Путь к файлу для сохранения логов',
        default=None
    )

    args = parser.parse_args()

    # Настройка логирования
    setup_logging(log_level=args.log_level, log_file=args.log_file)
    logger.info("=" * 70)
    logger.info("Запуск Web Parser")
    logger.info(f"Версия Python: {sys.version}")
    logger.info(f"Параметры: url={args.url}, timeout={args.timeout}, "
               f"log_level={args.log_level}")

    # Создаем парсер
    web_parser = WebParser(
        headless=not args.visible,
        timeout=args.timeout * 1000  # Конвертируем в миллисекунды
    )

    try:
        # Настраиваем браузер
        print("Инициализация браузера...", file=sys.stderr)
        logger.info("Инициализация браузера")
        web_parser.setup_browser(ignore_https_errors=args.ignore_https_errors)

        # Проверяем сертификаты
        certs = web_parser.get_windows_certificates()
        if certs:
            print(f"✓ Найдено сертификатов: {len(certs)}", file=sys.stderr)
        else:
            print("⚠ Сертификаты не найдены (сайт может не требовать клиентский сертификат)", file=sys.stderr)

        # Парсим страницу
        logger.info(f"Начало парсинга URL: {args.url}")
        start_time = time.time()

        result = web_parser.parse_page(
            args.url,
            wait_selector=args.wait_selector
        )

        parse_time = time.time() - start_time
        logger.info(f"Парсинг завершен за {parse_time:.2f} секунд")

        # Форматируем результат
        logger.debug("Форматирование результата в JSON")
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        logger.debug(f"Размер JSON: {len(output_json)} байт")

        # Сохраняем или выводим результат
        if args.output:
            output_path = Path(args.output)
            logger.info(f"Сохранение результата в файл: {output_path}")
            output_path.write_text(output_json, encoding='utf-8')
            print(f"\n✓ Результат сохранен в: {output_path}", file=sys.stderr)
            logger.info(f"Результат успешно сохранен: {output_path}")
        else:
            logger.debug("Вывод результата в stdout")
            print("\n" + output_json)

        logger.info("Web Parser завершен успешно")
        logger.info("=" * 70)
        return 0

    except KeyboardInterrupt:
        logger.warning("Получен сигнал прерывания от пользователя")
        print("\n\nПрервано пользователем", file=sys.stderr)
        return 130

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n✗ Ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        logger.info("Завершение работы, освобождение ресурсов")
        web_parser.close()


if __name__ == '__main__':
    sys.exit(main())
