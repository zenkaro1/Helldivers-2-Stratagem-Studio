@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Stratagem Studio] Erste Einrichtung - das dauert ein paar Minuten ...
    python -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)

if not exist ".venv\Scripts\pythonw.exe" goto :error
start "" ".venv\Scripts\pythonw.exe" -m app %*
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Start fehlgeschlagen.
echo Bitte "debug.cmd" ausfuehren - dort bleibt die Konsole offen und zeigt die Meldung.
if exist "%APPDATA%\HD2StratagemStudio\crash.log" (
    echo.
    echo --- crash.log ---
    type "%APPDATA%\HD2StratagemStudio\crash.log"
)
pause
exit /b 1
