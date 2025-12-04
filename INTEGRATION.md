# Примеры интеграции Web Parser

## Содержание
- [Пакетная обработка](#пакетная-обработка)
- [PowerShell интеграция](#powershell-интеграция)
- [Python интеграция](#python-интеграция)
- [Автоматизация по расписанию](#автоматизация-по-расписанию)
- [Обработка ошибок](#обработка-ошибок)

## Пакетная обработка

### Обработка списка URL из файла

Создайте файл `urls.txt`:
```
https://example.com
https://example.org
https://example.net
```

Batch-скрипт `parse_batch.bat`:
```batch
@echo off
setlocal enabledelayedexpansion

set PARSER=web-parser.exe
set OUTPUT_DIR=results

:: Создаем папку для результатов
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

:: Счетчик
set /a count=0
set /a success=0
set /a failed=0

:: Читаем URL из файла и обрабатываем
for /f "tokens=*" %%i in (urls.txt) do (
    set /a count+=1
    echo [!count!] Обработка: %%i

    :: Генерируем имя файла из URL
    set "url=%%i"
    set "filename=!url:~8!"
    set "filename=!filename:/=_!"
    set "filename=!filename::=_!"

    :: Парсим страницу
    %PARSER% "%%i" -o "%OUTPUT_DIR%\!filename!.json" --timeout 60

    if !errorlevel! equ 0 (
        echo ✓ Успешно: !filename!.json
        set /a success+=1
    ) else (
        echo ✗ Ошибка при обработке: %%i
        set /a failed+=1
    )
    echo.
)

echo ========================================
echo Обработка завершена
echo Всего: !count!
echo Успешно: !success!
echo Ошибок: !failed!
echo ========================================
pause
```

## PowerShell интеграция

### Базовый пример

```powershell
# Парсинг и получение JSON объекта
$result = & .\web-parser.exe "https://example.com" | ConvertFrom-Json

# Вывод информации
Write-Host "Заголовок: $($result.title)"
Write-Host "URL: $($result.url)"
Write-Host "Статус: $($result.status_code)"
Write-Host "Найдено ссылок: $($result.links.Count)"
Write-Host "Найдено изображений: $($result.images.Count)"
```

### Продвинутая обработка

```powershell
# parse_advanced.ps1

param(
    [string]$Url,
    [string]$OutputPath = "result.json",
    [int]$Timeout = 60
)

# Запуск парсера
Write-Host "Парсинг: $Url" -ForegroundColor Cyan

$startTime = Get-Date
$process = Start-Process -FilePath ".\web-parser.exe" `
    -ArgumentList $Url, "-o", $OutputPath, "--timeout", $Timeout `
    -Wait -PassThru -NoNewWindow

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

# Проверка результата
if ($process.ExitCode -eq 0) {
    Write-Host "✓ Успешно завершено за $([math]::Round($duration, 2)) секунд" -ForegroundColor Green

    # Читаем и анализируем результат
    $result = Get-Content $OutputPath | ConvertFrom-Json

    # Статистика
    Write-Host "`nСтатистика:" -ForegroundColor Yellow
    Write-Host "  Заголовок: $($result.title)"
    Write-Host "  Ссылок: $($result.links.Count)"
    Write-Host "  Изображений: $($result.images.Count)"
    Write-Host "  Форм: $($result.forms.Count)"
    Write-Host "  Размер HTML: $($result.html.Length) символов"
    Write-Host "  Размер текста: $($result.text.Length) символов"

    # Извлекаем уникальные домены из ссылок
    $domains = $result.links |
        ForEach-Object { ([System.Uri]$_.href).Host } |
        Where-Object { $_ -ne $null } |
        Select-Object -Unique

    Write-Host "`nУникальные домены в ссылках:"
    $domains | ForEach-Object { Write-Host "  - $_" }

} else {
    Write-Host "✗ Ошибка при парсинге (код: $($process.ExitCode))" -ForegroundColor Red
    exit $process.ExitCode
}
```

### Мониторинг изменений на сайте

```powershell
# monitor_changes.ps1

param(
    [string]$Url,
    [int]$IntervalMinutes = 60,
    [string]$BaselineFile = "baseline.json"
)

function Get-PageHash {
    param([string]$Content)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Content)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    $hash = $hasher.ComputeHash($bytes)
    return [BitConverter]::ToString($hash).Replace("-", "")
}

Write-Host "Мониторинг изменений на: $Url" -ForegroundColor Cyan
Write-Host "Интервал проверки: $IntervalMinutes минут`n"

# Первая проверка - создаем baseline
if (-not (Test-Path $BaselineFile)) {
    Write-Host "Создание baseline..." -ForegroundColor Yellow
    & .\web-parser.exe $Url -o $BaselineFile
    $baseline = Get-Content $BaselineFile | ConvertFrom-Json
    $baselineHash = Get-PageHash $baseline.html
    Write-Host "✓ Baseline создан. Hash: $baselineHash`n" -ForegroundColor Green
} else {
    $baseline = Get-Content $BaselineFile | ConvertFrom-Json
    $baselineHash = Get-PageHash $baseline.html
    Write-Host "Используется существующий baseline. Hash: $baselineHash`n"
}

# Бесконечный цикл мониторинга
while ($true) {
    $checkTime = Get-Date
    Write-Host "[$checkTime] Проверка изменений..." -ForegroundColor Cyan

    # Парсим страницу
    $tempFile = "temp_$(Get-Date -Format 'yyyyMMddHHmmss').json"
    & .\web-parser.exe $Url -o $tempFile

    if (Test-Path $tempFile) {
        $current = Get-Content $tempFile | ConvertFrom-Json
        $currentHash = Get-PageHash $current.html

        if ($currentHash -ne $baselineHash) {
            Write-Host "⚠ ОБНАРУЖЕНЫ ИЗМЕНЕНИЯ!" -ForegroundColor Red
            Write-Host "  Baseline hash: $baselineHash"
            Write-Host "  Current hash:  $currentHash"

            # Сохраняем изменившуюся версию
            $changedFile = "changed_$(Get-Date -Format 'yyyyMMddHHmmss').json"
            Copy-Item $tempFile $changedFile
            Write-Host "  Сохранено в: $changedFile"

            # Можно добавить отправку уведомлений
            # Send-MailMessage ...

            # Обновляем baseline
            Copy-Item $tempFile $BaselineFile
            $baselineHash = $currentHash
            Write-Host "  Baseline обновлен`n"
        } else {
            Write-Host "✓ Изменений не обнаружено`n" -ForegroundColor Green
        }

        Remove-Item $tempFile
    } else {
        Write-Host "✗ Ошибка при парсинге`n" -ForegroundColor Red
    }

    Write-Host "Следующая проверка через $IntervalMinutes минут..."
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
```

## Python интеграция

### Простой пример

```python
import subprocess
import json
from pathlib import Path

def parse_website(url, output_file=None, timeout=60):
    """
    Парсит веб-сайт используя web-parser.exe

    Args:
        url: URL страницы
        output_file: Путь к файлу для сохранения (опционально)
        timeout: Таймаут в секундах

    Returns:
        dict: Результат парсинга
    """
    cmd = ['web-parser.exe', url, '--timeout', str(timeout)]

    if output_file:
        cmd.extend(['-o', str(output_file)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,  # Добавляем запас
            encoding='utf-8'
        )

        if result.returncode == 0:
            if output_file and Path(output_file).exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return json.loads(result.stdout)
        else:
            raise RuntimeError(f"Parser failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Parsing timeout after {timeout} seconds")

# Использование
if __name__ == '__main__':
    result = parse_website('https://example.com')

    print(f"Title: {result['title']}")
    print(f"Links: {len(result['links'])}")
    print(f"Images: {len(result['images'])}")
```

### Класс-обертка

```python
# web_parser_wrapper.py

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ParseResult:
    """Результат парсинга"""
    url: str
    title: str
    status_code: int
    html: str
    text: str
    links: List[Dict[str, str]]
    forms: List[Dict[str, Any]]
    images: List[Dict[str, str]]
    metadata: Dict[str, Any]
    parse_time: datetime

class WebParserClient:
    """Клиент для работы с web-parser.exe"""

    def __init__(self, parser_path: str = 'web-parser.exe'):
        self.parser_path = Path(parser_path)
        if not self.parser_path.exists():
            raise FileNotFoundError(f"Parser not found: {parser_path}")

    def parse(
        self,
        url: str,
        timeout: int = 60,
        wait_selector: Optional[str] = None,
        ignore_https_errors: bool = False,
        visible: bool = False
    ) -> ParseResult:
        """
        Парсит веб-страницу

        Args:
            url: URL страницы
            timeout: Таймаут в секундах
            wait_selector: CSS селектор для ожидания
            ignore_https_errors: Игнорировать SSL ошибки
            visible: Показывать окно браузера

        Returns:
            ParseResult: Результат парсинга
        """
        logger.info(f"Parsing: {url}")

        cmd = [
            str(self.parser_path),
            url,
            '--timeout', str(timeout)
        ]

        if wait_selector:
            cmd.extend(['--wait-selector', wait_selector])
        if ignore_https_errors:
            cmd.append('--ignore-https-errors')
        if visible:
            cmd.append('--visible')

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 30,
                encoding='utf-8'
            )

            if result.returncode != 0:
                logger.error(f"Parser failed: {result.stderr}")
                raise RuntimeError(f"Parser error: {result.stderr}")

            data = json.loads(result.stdout)
            parse_time = datetime.now()

            logger.info(f"✓ Parsed successfully in {(parse_time - start_time).total_seconds():.2f}s")

            return ParseResult(
                url=data['url'],
                title=data['title'],
                status_code=data['status_code'],
                html=data['html'],
                text=data['text'],
                links=data['links'],
                forms=data['forms'],
                images=data['images'],
                metadata=data['metadata'],
                parse_time=parse_time
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout after {timeout}s")
            raise TimeoutError(f"Parsing timeout: {url}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Invalid JSON response: {e}")

    def parse_multiple(
        self,
        urls: List[str],
        **kwargs
    ) -> Dict[str, Optional[ParseResult]]:
        """
        Парсит несколько URL

        Args:
            urls: Список URL
            **kwargs: Параметры для parse()

        Returns:
            Dict[str, ParseResult]: Словарь {url: result}
        """
        results = {}

        for url in urls:
            try:
                results[url] = self.parse(url, **kwargs)
            except Exception as e:
                logger.error(f"Failed to parse {url}: {e}")
                results[url] = None

        return results

# Пример использования
if __name__ == '__main__':
    client = WebParserClient()

    # Один URL
    result = client.parse('https://example.com')
    print(f"Title: {result.title}")
    print(f"Links: {len(result.links)}")

    # Несколько URL
    urls = [
        'https://example.com',
        'https://example.org',
        'https://example.net'
    ]

    results = client.parse_multiple(urls)

    for url, result in results.items():
        if result:
            print(f"{url}: {result.title}")
        else:
            print(f"{url}: FAILED")
```

## Автоматизация по расписанию

### Windows Task Scheduler

1. Создайте batch-скрипт `scheduled_parse.bat`:

```batch
@echo off
cd /d "C:\path\to\web-parser-app"

set URL=https://example.com
set OUTPUT=results\result_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.json

web-parser.exe %URL% -o %OUTPUT% --timeout 120

if errorlevel 1 (
    echo Parsing failed >> error.log
)
```

2. Создайте задачу в Task Scheduler:
   - Откройте Task Scheduler
   - Create Task
   - Triggers → New → Задайте расписание
   - Actions → New → Укажите путь к `scheduled_parse.bat`

### Cron-подобная задача через PowerShell

```powershell
# schedule_parsing.ps1

$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\path\to\your\parse_script.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

Register-ScheduledTask -TaskName "WebParser_Daily" `
    -Action $action `
    -Trigger $trigger `
    -Description "Ежедневный парсинг веб-сайта"
```

## Обработка ошибок

### Retry с экспоненциальной задержкой

```python
import time
import subprocess
import json
from typing import Optional

def parse_with_retry(
    url: str,
    max_retries: int = 3,
    base_delay: float = 2.0
) -> Optional[dict]:
    """
    Парсинг с повторными попытками

    Args:
        url: URL страницы
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка между попытками

    Returns:
        dict или None
    """
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ['web-parser.exe', url],
                capture_output=True,
                text=True,
                timeout=90,
                encoding='utf-8'
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                raise RuntimeError(result.stderr)

        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"All {max_retries} attempts failed")
                return None

    return None

# Использование
result = parse_with_retry('https://example.com')
if result:
    print(f"Success: {result['title']}")
else:
    print("Failed after all retries")
```

---

Эти примеры помогут интегрировать Web Parser в ваши рабочие процессы и автоматизировать парсинг веб-страниц.
