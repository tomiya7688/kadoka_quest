@echo off
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
