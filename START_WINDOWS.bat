@echo off
setlocal
cd /d "%~dp0"
title LidGuard Prototype
where py >nul 2>nul
if errorlevel 1 goto use_python
set "LIDGUARD_PY=py -3"
goto check_python
:use_python
set "LIDGUARD_PY=python"
:check_python
%LIDGUARD_PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 goto python_missing
if exist ".venv\Scripts\python.exe" goto check_dependencies
echo Creating the project's Python environment...
%LIDGUARD_PY% -m venv .venv
if errorlevel 1 goto setup_failed
:check_dependencies
".venv\Scripts\python.exe" -c "import numpy; from PIL import Image" >nul 2>nul
if not errorlevel 1 goto run_app
echo Installing NumPy and Pillow. This first setup needs internet access...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed
:run_app
echo.
echo Starting LidGuard at http://localhost:8765
echo Keep this window open. Press Ctrl+C here when you finish.
echo.
".venv\Scripts\python.exe" app.py --open-browser
if errorlevel 1 goto setup_failed
exit /b 0
:python_missing
echo.
echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/windows/
echo Then close this window and run START_WINDOWS.bat again.
pause
exit /b 1
:setup_failed
echo.
echo LidGuard could not complete setup or start. Keep the error above.
echo Check README.md or send a screenshot of this window for help.
pause
exit /b 1
