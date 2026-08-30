@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launcher.py
) else (
  py launcher.py
)
if errorlevel 1 pause


