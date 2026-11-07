@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
  echo Git fehlt: https://git-scm.com/download/win
  pause
  exit /b 1
)

if not exist ".git" (
  echo Kein Git-Repository - bitte zuerst publish-to-github.cmd ausfuehren.
  pause
  exit /b 1
)

set "VERSION=%~1"
if "%VERSION%"=="" set /p "VERSION=Version (z. B. v1.0.0): "
if "%VERSION%"=="" (
  echo Keine Version angegeben.
  pause
  exit /b 1
)

echo.
echo Erstelle Tag %VERSION% und pushe ihn ...
git tag -a "%VERSION%" -m "Stratagem Studio %VERSION%"
if errorlevel 1 (
  echo Tag konnte nicht erstellt werden - existiert er schon?
  pause
  exit /b 1
)
git push origin "%VERSION%"
if errorlevel 1 (
  echo Push des Tags fehlgeschlagen.
  pause
  exit /b 1
)

echo.
echo Fertig. GitHub Actions baut jetzt die Setup-ZIP und legt das Release an:
echo    https://github.com/zenkaro1/Helldivers-2-Stratagem-Studio/releases
echo.
pause
