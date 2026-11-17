@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0installer\Select.ps1" uninstall
if errorlevel 1 pause
