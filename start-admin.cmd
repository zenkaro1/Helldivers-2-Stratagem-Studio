@echo off
rem Startet Stratagem Studio mit Administratorrechten.
rem Noetig, wenn Helldivers 2 selbst als Administrator laeuft: sonst ignoriert
rem Windows sowohl die Hotkey-Erkennung als auch die gesendeten Tasten.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Bitte zuerst start.cmd ausfuehren - die Einrichtung fehlt noch.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process -FilePath '%~dp0.venv\Scripts\pythonw.exe' -ArgumentList '-m','app' -WorkingDirectory '%~dp0' -Verb RunAs"
