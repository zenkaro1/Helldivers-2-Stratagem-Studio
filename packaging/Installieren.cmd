@echo off
setlocal EnableExtensions
title Stratagem Studio installieren

set "SOURCE=%~dp0StratagemStudio"
set "TARGET=%LOCALAPPDATA%\Programs\StratagemStudio"

if not exist "%SOURCE%\StratagemStudio.exe" (
    echo FEHLER: StratagemStudio.exe fehlt neben diesem Skript.
    pause
    exit /b 1
)

echo.
echo   Stratagem Studio wird installiert nach:
echo   %TARGET%
echo.

if not exist "%TARGET%" mkdir "%TARGET%" >nul 2>&1
robocopy "%SOURCE%" "%TARGET%" /E /XD userdata /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo FEHLER beim Kopieren. Laeuft die App gerade? Bitte schliessen und erneut versuchen.
    pause
    exit /b 1
)

echo Entferne Windows-Downloadsperre ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath $env:TARGET -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1

echo Erstelle Verknuepfungen ...
set "TARGET_DIR=%TARGET%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $exe = Join-Path $env:TARGET_DIR 'StratagemStudio.exe'; $dirs = @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs')); foreach ($d in $dirs) { $lnk = $ws.CreateShortcut((Join-Path $d 'Stratagem Studio.lnk')); $lnk.TargetPath = $exe; $lnk.WorkingDirectory = $env:TARGET_DIR; $lnk.IconLocation = $exe + ',0'; $lnk.Save() }" >nul 2>&1

echo.
echo Fertig. Verknuepfung liegt auf dem Desktop und im Startmenue.
echo.
choice /C JN /N /M "Jetzt starten? [J/N] "
if errorlevel 2 goto :done
start "" "%TARGET%\StratagemStudio.exe"

:done
echo.
pause

