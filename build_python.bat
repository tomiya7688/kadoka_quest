@echo off
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

:failed
echo.
echo [failed] Distribution build or smoke test failed.
pause
exit /b 1
