@echo off
chcp 65001 >nul
echo ========================================
echo Web Parser - Скрипт сборки
echo ========================================
echo.

:: Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH!
    echo Установите Python 3.8+ с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Создание виртуального окружения...
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
)

echo [2/5] Активация виртуального окружения...
call venv\Scripts\activate.bat

echo [3/5] Установка зависимостей...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости
    pause
    exit /b 1
)

echo [4/5] Установка браузеров Playwright...
python -m playwright install chromium
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить браузеры Playwright
    pause
    exit /b 1
)

echo [5/5] Сборка EXE файла с помощью PyInstaller...
if exist dist\web-parser.exe del /f dist\web-parser.exe
pyinstaller --clean web_parser.spec
if errorlevel 1 (
    echo [ОШИБКА] Не удалось собрать EXE файл
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✓ Сборка завершена успешно!
echo ========================================
echo.
echo Исполняемый файл: dist\web-parser.exe
echo.
echo ВАЖНО: Для работы приложения необходимо:
echo 1. Скопировать папку playwright/driver рядом с exe
echo 2. Или установить Playwright браузеры на целевой машине
echo.
pause
