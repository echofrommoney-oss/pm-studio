@echo off
rem PM Console launcher (Windows). Double-click, keep this window open;
rem closing it stops the console. This file stays pure ASCII on purpose:
rem cmd.exe reads batch text with the OEM codepage, so Chinese here would break.
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
py -3 -c "print('PMPYOK')" 2>nul | findstr /C:"PMPYOK" >nul && set "PY=py -3"
if not defined PY python -c "print('PMPYOK')" 2>nul | findstr /C:"PMPYOK" >nul && set "PY=python"
if not defined PY (
  echo Python 3.9+ not found. Install from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)
%PY% scripts\pm_console.py --open
pause
