@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" developer_launcher.py
) else (
  py developer_launcher.py
)
if errorlevel 1 pause
