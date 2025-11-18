# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Arduino IDE Modern
Creates a standalone executable with all dependencies bundled
"""

import os
import sys
from pathlib import Path

block_cipher = None

# Base directory of the project
base_dir = Path(SPECPATH)

# Determine executable name based on platform
if sys.platform == 'win32':
    exe_name = 'Arduino-IDE.exe'
else:
    exe_name = 'Arduino-IDE'

# Collect all data files that need to be bundled
datas = [
    # Resources directory (snippets and templates)
    (str(base_dir / 'arduino_ide' / 'resources'), 'arduino_ide/resources'),

    # Data directory (API references)
    (str(base_dir / 'arduino_ide' / 'data'), 'arduino_ide/data'),

    # Arduino cores directory
    (str(base_dir / 'arduino_ide' / 'cores'), 'arduino_ide/cores'),

    # Arduino CLI helper script
    (str(base_dir / 'arduino-cli'), '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSerialPort',
    'pygments.lexers.c_cpp',
    'pygments.lexers.python',
    'pygments.formatters.html',
    'jedi',
]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI application (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
