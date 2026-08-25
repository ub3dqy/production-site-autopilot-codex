@echo off
setlocal
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0scripts\verify_local.py" %*
  exit /b %errorlevel%
)
python "%~dp0scripts\verify_local.py" %*
exit /b %errorlevel%
