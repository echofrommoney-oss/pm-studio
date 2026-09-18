@echo off
rem PM Studio project overview (Windows). Double-click, keep this window open.
rem Pure ASCII on purpose: cmd.exe reads batch text with the OEM codepage.
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
py -3 -c "print('PMPYOK')" 2>nul | findstr /C:"PMPYOK" >nul && set "PY=py -3"
if not defined PY python -c "print('PMPYOK')" 2>nul | findstr /C:"PMPYOK" >nul && set "PY=python"
if not defined PY (
  echo Python 3.9+ not found. Install from https://www.python.org/downloads/
  pause
  exit /b 1
)
%PY% hub\pm_hub.py --open
pause
