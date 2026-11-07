@echo off
rem Baut die App mit PyInstaller (Ordner-Build, inkl. Logo-Icon und Sprachmodulen).
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Bitte zuerst start.cmd ausfuehren - die Umgebung fehlt noch.
    pause
    exit /b 1
)

echo [1/3] PyInstaller installieren ...
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

echo [2/3] Sprachmodule einsammeln ...
echo (faster-whisper, ctranslate2, onnxruntime, sounddevice)

echo [3/3] App bauen ...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name "StratagemStudio" ^
  --icon "app\assets\logo.ico" ^
  --add-data "data;data" ^
  --add-data "app\assets;app/assets" ^
  --hidden-import "PySide6.QtSvg" ^
  --hidden-import "requests" ^
  --collect-all "faster_whisper" ^
  --collect-all "ctranslate2" ^
  --collect-all "tokenizers" ^
  --collect-all "av" ^
  --collect-all "onnxruntime" ^
  --collect-all "sounddevice" ^
  --collect-all "huggingface_hub" ^
  launcher.py
if errorlevel 1 goto :error

echo.
echo Fertig: dist\StratagemStudio\StratagemStudio.exe
echo Der ganze Ordner ist die App - zum Weitergeben den Ordner kopieren/zippen.
pause
exit /b 0

:error
echo.
echo Bau fehlgeschlagen - siehe Ausgabe oben.
pause
exit /b 1
