@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Arbeitsordner: %CD%
echo.

if not exist "launcher.py" (
  echo FEHLER: launcher.py fehlt - bitte im Projektordner ausfuehren.
  pause
  exit /b 1
)
if not exist "app\main.py" (
  echo FEHLER: app\main.py fehlt.
  pause
  exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
  echo Git ist nicht installiert. Bitte installieren:
  echo https://git-scm.com/download/win
  pause
  exit /b 1
)

set "REPO=%~1"
if "%REPO%"=="" set "REPO=https://github.com/zenkaro1/hd2-stratagem-studio.git"
if "%~1"=="" set /p "REPO=Repository-URL [Enter fuer %REPO%]: "
if "%REPO%"=="" set "REPO=https://github.com/zenkaro1/hd2-stratagem-studio.git"

if not exist ".git" (
  git init -b main
)

git config user.name >nul 2>&1 || git config user.name "zenkaro1"
git config user.email >nul 2>&1 || git config user.email "zenkaro1@users.noreply.github.com"

echo.
echo Dateien werden vorgemerkt ...
git add -A

set "COUNT=0"
for /f %%c in ('git ls-files ^| find /c /v ""') do set "COUNT=%%c"
echo Verfolgte Dateien: %COUNT%
if %COUNT% LSS 30 (
  echo.
  echo FEHLER: Nur %COUNT% Dateien gefunden - falscher Ordner?
  git status --short
  pause
  exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Stratagem Studio: Loadout-, Makro- und Sprach-Tool fuer Helldivers 2"
) else (
  echo Keine neuen Aenderungen.
)

git remote remove origin >nul 2>&1
git remote add origin "%REPO%"
git config http.postBuffer 524288000

echo.
echo Push nach %REPO% ...
git push -u origin main
if errorlevel 1 (
  echo.
  echo Push fehlgeschlagen. Haeufige Ursachen:
  echo 1. Repository existiert noch nicht - auf github.com/new ein LEERES Repo anlegen.
  echo 2. Repo ist nicht leer - dann: git pull --rebase origin main
  echo 3. Login: Personal Access Token statt Passwort (GitHub zeigt ein Fenster).
  echo.
  echo Lokal sind %COUNT% Dateien committet und warten auf den Push.
  pause
  exit /b 1
)

echo.
echo Fertig: %COUNT% Dateien sind auf GitHub.
set "REPO_WEB=%REPO:.git=%"
echo.
echo Naechster Schritt - erstes Release bauen:
echo    make-release.cmd
echo oder manuell:
echo    git tag v1.0.0 ^&^& git push origin v1.0.0
echo.
start "" "%REPO_WEB%"
pause
