@echo off
cd /d "%~dp0"
echo Arfa setup starting... > "%~dp0setup_started.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_arfa.ps1" %*
echo.
echo Finished. You can close this window.
pause
