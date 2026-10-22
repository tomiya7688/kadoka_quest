@echo off
rem {
rem   Responsibility: [start_task: Find the next prioritized open GitHub Issue; prefer migration at P1]
rem   Action: [1: Find the next prioritized open GitHub Issue; prefer migration at P1]
rem   Param: [argv: Command-line arguments; fixed-target entries may ignore them]
rem   Return: [status: Exit status set by the entry script or delegated command]
rem }
setlocal EnableExtensions EnableDelayedExpansion

where gh >nul 2>&1
if errorlevel 1 (
  echo [ERROR] GitHub CLI ^(gh^) was not found in PATH.
  exit /b 1
)

call gh auth status >nul 2>&1
if errorlevel 1 (
  echo [ERROR] GitHub CLI is not authenticated. Run: gh auth login
  exit /b 1
)

set "ISSUE_NUMBER="
set "ISSUE_PRIORITY="

for %%P in ("priority: p0" "priority: p1" "priority: p2" "priority: p3" "priority: p4") do (
  if not defined ISSUE_NUMBER (
    if "%%~P"=="priority: p1" call :find_issue "%%~P" "gdscript"
    if not defined ISSUE_NUMBER call :find_issue "%%~P" ""
  )
)

if not defined ISSUE_NUMBER (
  echo [INFO] No open prioritized Issue was found.
  exit /b 2
)

echo Priority: !ISSUE_PRIORITY!
echo.
call gh issue view !ISSUE_NUMBER!
exit /b %ERRORLEVEL%

rem {
rem   Responsibility: [find_issue: Select the first matching prioritized Issue]
rem   Action: [1: Query GitHub CLI and keep the selected number and priority]
rem   Param: [
rem     1: Priority label
rem     2: Optional classification label
rem   ]
rem   Return: [status: Exit code 0; the result is stored in batch variables]
rem }
:find_issue
set "TASK_LABEL_FILTER="
if not "%~2"=="" set "TASK_LABEL_FILTER=--label %~2"
for /f "usebackq delims=" %%I in (`gh issue list --state open --label "%~1" !TASK_LABEL_FILTER! --limit 20 --search "sort:created-asc" --json number --jq ".[].number" 2^>nul`) do (
  if not defined ISSUE_NUMBER (
    set "ISSUE_NUMBER=%%I"
    set "ISSUE_PRIORITY=%~1"
  )
)
exit /b 0
