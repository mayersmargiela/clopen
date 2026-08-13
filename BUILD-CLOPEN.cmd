@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Clopen Builder

echo ========================================
echo           Clopen Windows Builder
echo ========================================
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto :deps

set "BOOTSTRAP_PY="
py -3.12 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PY=py -3.12"

if not defined BOOTSTRAP_PY (
  py -3.11 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
  if not errorlevel 1 set "BOOTSTRAP_PY=py -3.11"
)

if not defined BOOTSTRAP_PY (
  python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
  if not errorlevel 1 set "BOOTSTRAP_PY=python"
)

if not defined BOOTSTRAP_PY (
  echo [ERROR] Python 3.11 or newer was not found.
  echo Install 64-bit Python 3.12 from python.org, then run this file again.
  echo During setup, enabling "Add python.exe to PATH" is recommended.
  echo.
  pause
  exit /b 1
)

echo [1/4] Creating project environment...
%BOOTSTRAP_PY% -m venv "%~dp0.venv"
if errorlevel 1 goto :failed

:deps
echo [2/4] Checking build dependencies...
"%VENV_PY%" -c "import PySide6, PyInstaller" >nul 2>nul
if errorlevel 1 (
  echo Installing PySide6 and PyInstaller. This is only needed the first time...
  "%VENV_PY%" -m pip install --upgrade pip
  if errorlevel 1 goto :failed
  "%VENV_PY%" -m pip install -e ".[build]"
  if errorlevel 1 goto :failed
)

echo Running unit tests in offscreen mode...
set "QT_QPA_PLATFORM=offscreen"
set "PYTHONPATH=%~dp0src"
set "PYTHONDONTWRITEBYTECODE=1"
"%VENV_PY%" -m unittest discover -s tests -v
if errorlevel 1 goto :failed

echo Running release self-check...
"%VENV_PY%" "%~dp0tools\release_selfcheck.py"
if errorlevel 1 goto :failed

echo [3/4] Building Clopen.exe...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
if errorlevel 1 goto :failed

echo [4/4] Build complete.
set "OUTDIR=%~dp0dist\Clopen"
echo.
echo Output folder:
echo %OUTDIR%
echo.
if exist "%OUTDIR%\Clopen.exe" explorer.exe "%OUTDIR%"
pause
exit /b 0

:failed
echo.
echo [ERROR] Build failed.
echo Keep this window open and send the error text or a screenshot back to ChatGPT.
echo.
pause
exit /b 1
