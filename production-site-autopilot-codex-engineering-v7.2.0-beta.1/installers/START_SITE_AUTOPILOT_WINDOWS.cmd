@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -ProjectPath "%~1"
if errorlevel 1 exit /b %errorlevel%
echo.
echo Open the project in Codex and invoke Production Site Autopilot.
