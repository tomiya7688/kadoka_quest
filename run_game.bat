@echo off
rem {
rem   Responsibility: [run_game: Launch the Player launcher through scripts/run_python.bat]
rem   Action: [1: Delegate launcher.py and pause on failure]
rem   Param: [argv: Command-line arguments; fixed-target entries may ignore them]
rem   Return: [status: Exit status set by the entry script or delegated command]
rem }
call "%~dp0scripts\run_python.bat" launcher.py
if errorlevel 1 pause


