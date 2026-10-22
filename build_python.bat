@echo off
rem {
rem   Responsibility: [build_python: Build and smoke-test the selected distributions with PyInstaller]
rem   Action: [1: Select Python, ensure build dependencies, then delegate build and smoke checks]
rem   Param: [argv: Command-line arguments; fixed-target entries may ignore them]
rem   Return: [status: Exit status set by the entry script or delegated command]
rem }
setlocal
cd /d "%~dp0"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=all"

set "PYTHON=py"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

%PYTHON% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo [build] Installing build dependencies...
  %PYTHON% -m pip install -r requirements-build.txt
  if errorlevel 1 goto :failed
)

%PYTHON% tools\build\build.py --clean --targets %TARGET%
if errorlevel 1 goto :failed

%PYTHON% tools\build\test_distribution.py --targets %TARGET%
if errorlevel 1 goto :failed

echo.
echo [ok] Kadoka Quest distribution build and smoke test completed.
exit /b 0

rem {
rem   Responsibility: [failed: Report a failed distribution build or smoke test]
rem   Action: [1: Print the failure message and pause before exiting]
rem   Param: []
rem   Return: [status: Exit code 1]
rem }
:failed
echo.
echo [failed] Distribution build or smoke test failed.
pause
exit /b 1
