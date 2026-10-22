@echo off
rem {
rem   Responsibility: [run_python: Select a project virtual environment and run the requested Python command]
rem   Action: [1: Select a project virtual environment and run the requested Python command]
rem   Param: [argv: Command-line arguments; fixed-target entries may ignore them]
rem   Return: [status: Exit status set by the entry script or delegated command]
rem }
setlocal

set "PROJECT_ROOT=%~dp0.."
set "KADOKA_PYTHON=%PROJECT_ROOT%\venv_3135\Scripts\python.exe"
for %%G in (git.exe) do if not defined KADOKA_GIT_EXECUTABLE set "KADOKA_GIT_EXECUTABLE=%%~$PATH:G"

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
