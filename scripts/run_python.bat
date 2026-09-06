@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "KADOKA_PYTHON=%PROJECT_ROOT%\venv_3135\Scripts\python.exe"

if exist "%KADOKA_PYTHON%" (
  rem Keep pygame's bundled DLLs ahead of unavailable Python installations.
  set "PATH=%PROJECT_ROOT%\venv_3135\Lib\site-packages\pygame;%PROJECT_ROOT%\venv_3135\Scripts;%SystemRoot%\System32;%SystemRoot%"
) else (
  set "KADOKA_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
)

if not exist "%KADOKA_PYTHON%" (
  echo Python virtual environment was not found.
  echo Create venv_3135 with: py -3.13 -m venv venv_3135
  exit /b 1
)

pushd "%PROJECT_ROOT%"
"%KADOKA_PYTHON%" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
