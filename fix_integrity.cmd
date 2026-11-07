@echo off
rem Entfernt die "Niedrige Verbindlichkeitsstufe" von App und Projektordner.
rem Ursache: Wurden die Dateien von einem eingeschraenkten Prozess erzeugt,
rem laeuft die EXE dadurch selbst mit niedrigen Rechten - Windows blockiert
rem dann Tastatur-Hooks und Makros gegenueber dem Spiel.
setlocal
cd /d "%~dp0"

echo Setze Integritaetsstufe auf "Mittel" ...
icacls "%~dp0" /setintegritylevel Medium >nul 2>&1
icacls "%~dp0app" /setintegritylevel Medium /T /C /Q >nul 2>&1
icacls "%~dp0dist" /setintegritylevel Medium /T /C /Q >nul 2>&1
icacls "%~dp0.venv\Scripts\python.exe" /setintegritylevel Medium >nul 2>&1
icacls "%~dp0.venv\Scripts\pythonw.exe" /setintegritylevel Medium >nul 2>&1
icacls "%~dp0launcher.py" /setintegritylevel Medium >nul 2>&1

echo.
echo Kontrolle:
icacls "%~dp0dist\StratagemStudio\StratagemStudio.exe" | findstr /I "Verbindliche Mandatory"
if errorlevel 1 (
    echo   Kein Label gefunden - gut ^(Standard = Mittel^).
) else (
    echo   Steht dort "Niedrige"/"Low", hat das Skript keine Rechte:
    echo   Bitte per Rechtsklick "Als Administrator ausfuehren" starten.
)

echo.
echo Danach dist\StratagemStudio\StratagemStudio.exe neu starten.
pause
