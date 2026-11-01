@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto fail
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install "pyinstaller>=6,<7"
if errorlevel 1 goto fail

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name SipCat --add-data "assets:assets" main.py
if errorlevel 1 goto fail

rem Test the new executable itself on Windows, including bundled sprites and dashboard.
"dist\SipCat.exe" --self-check
if errorlevel 1 goto check_fail
echo Build complete: %~dp0dist\SipCat.exe
exit /b 0

:check_fail
echo Packaged executable failed its dashboard check. Do not use this build.
if exist "dist\SipCat.exe" del "dist\SipCat.exe"
exit /b 1

:fail
echo Build failed. Read the error messages above.
if exist "dist\SipCat.exe" del "dist\SipCat.exe"
exit /b 1
