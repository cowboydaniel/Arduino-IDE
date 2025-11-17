@echo off
REM Build script for creating standalone Arduino IDE .exe
REM Double-click this file on Windows to build the executable

echo ======================================================================
echo Arduino IDE Modern - Standalone .exe Builder
echo ======================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://www.python.org/
    pause
    exit /b 1
)

REM Run the build script
python build_exe.py

echo.
echo Press any key to exit...
pause >nul
