# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec файл для упаковки Web Parser
"""

import os
import sys
from pathlib import Path

# Определяем пути
block_cipher = None
project_dir = Path(os.path.abspath(SPECPATH))

# Находим путь к Playwright драйверам
playwright_driver = None
for site_packages in sys.path:
    playwright_path = Path(site_packages) / 'playwright' / 'driver'
    if playwright_path.exists():
        playwright_driver = str(playwright_path)
        break

# Собираем дополнительные файлы
datas = []
binaries = []

# Добавляем Playwright драйверы если найдены
if playwright_driver:
    datas.append((playwright_driver, 'playwright/driver'))

a = Analysis(
    ['web_parser.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'playwright',
        'playwright.sync_api',
        'greenlet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='web-parser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Консольное приложение
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
