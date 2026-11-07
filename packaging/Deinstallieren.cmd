@echo off
setlocal EnableExtensions
title Stratagem Studio deinstallieren

set "TARGET=%LOCALAPPDATA%\Programs\StratagemStudio"

echo.
echo   Entfernt Stratagem Studio und alle Einstellungen/Loadouts.
echo   Ordner: %TARGET%
echo.
choice /C JN /N /M "Wirklich deinstallieren? [J/N] "
if errorlevel 2 goto :done

echo Entferne Verknuepfungen ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $paths = @((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Stratagem Studio.lnk'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Stratagem Studio.lnk')); foreach ($p in $paths) { if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue } }" >nul 2>&1

echo Entferne Programmordner ...
if exist "%TARGET%" rmdir /S /Q "%TARGET%"

echo.
echo Fertig.
echo.
pause

:done
