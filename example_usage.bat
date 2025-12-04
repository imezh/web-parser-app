@echo off
chcp 65001 >nul
echo ========================================
echo Web Parser - Примеры использования
echo ========================================
echo.

:: Проверяем наличие собранного EXE
if not exist "dist\web-parser.exe" (
    echo [ОШИБКА] Файл web-parser.exe не найден!
    echo Сначала запустите build.bat для сборки приложения.
    echo.
    pause
    exit /b 1
)

set PARSER=dist\web-parser.exe

echo [Пример 1] Простой парсинг с выводом в консоль
echo Команда: %PARSER% https://example.com
echo.
pause

%PARSER% https://example.com
echo.
echo ----------------------------------------
echo.

echo [Пример 2] Сохранение результата в файл
echo Команда: %PARSER% https://example.com -o example_result.json
echo.
pause

%PARSER% https://example.com -o example_result.json
if exist example_result.json (
    echo ✓ Результат сохранен в example_result.json
    echo.
    echo Первые 500 символов:
    powershell -Command "Get-Content example_result.json -Raw | Select-Object -First 1 | ForEach-Object { $_.Substring(0, [Math]::Min(500, $_.Length)) }"
)
echo.
echo ----------------------------------------
echo.

echo [Пример 3] Парсинг с увеличенным таймаутом
echo Команда: %PARSER% https://example.com --timeout 120
echo.
pause

%PARSER% https://example.com --timeout 120
echo.
echo ----------------------------------------
echo.

echo [Пример 4] Отладка с видимым окном браузера
echo Команда: %PARSER% https://example.com --visible
echo (Вы увидите окно браузера)
echo.
pause

%PARSER% https://example.com --visible
echo.
echo ----------------------------------------
echo.

echo [Пример 5] Справка по всем параметрам
echo Команда: %PARSER% --help
echo.
pause

%PARSER% --help
echo.
echo ----------------------------------------
echo.

echo ✓ Все примеры выполнены!
echo.
pause
