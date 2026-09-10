@echo off
call "%~dp0build_python.bat" player
exit /b %errorlevel%
