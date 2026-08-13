@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist "python\python.exe" (
  echo FEHLER: python\python.exe fehlt.
  echo Bitte den Ordner neu aus dem ZIP entpacken.
  pause
  exit /b 1
)

echo Starte Zeltplatz Buchung Testsystem ...
set PYTHONUNBUFFERED=1
python\python.exe launch.py
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  pause
)
exit /b %ERR%
