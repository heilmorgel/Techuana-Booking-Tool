@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Setzt das Testsystem auf die Demodaten zurueck.
echo Alle selbst angelegten Buchungen gehen verloren.
echo.
choice /C JN /M "Jetzt zuruecksetzen"
if errorlevel 2 exit /b 0

call "%~dp0Stop.bat"
timeout /t 2 /nobreak >nul

if exist "%~dp0data\booking.db" del /f /q "%~dp0data\booking.db"
if exist "%~dp0data\booking.db-wal" del /f /q "%~dp0data\booking.db-wal"
if exist "%~dp0data\booking.db-shm" del /f /q "%~dp0data\booking.db-shm"

echo.
echo Demodaten werden beim naechsten Start neu angelegt.
echo.
call "%~dp0Start.bat"
