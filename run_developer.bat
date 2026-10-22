@echo off
rem {
rem   Responsibility: [run_developer: Launch the Developer launcher with .venv Python or py fallback]
rem   Action: [1: Select the interpreter, launch developer_launcher.py and pause on failure]
rem   Param: [argv: Command-line arguments; fixed-target entries may ignore them]
rem   Return: [status: Exit status set by the entry script or delegated command]
rem }
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" developer_launcher.py
) else (
  py developer_launcher.py
)
if errorlevel 1 pause
