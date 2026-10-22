@echo off
rem {
rem   Responsibility: [build_player: Build the Player distribution through build_python.bat]
rem   Action: [1: Delegate with the player target and return its exit status]
rem   Param: [argv: Command-line arguments; fixed-target entries may ignore them]
rem   Return: [status: Exit status set by the entry script or delegated command]
rem }
call "%~dp0build_python.bat" player
exit /b %errorlevel%
