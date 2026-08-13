@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "PIDFILE=%~dp0data\server.pid"
if exist "%PIDFILE%" (
  set /p PID=<"%PIDFILE%"
  if not "!PID!"=="" (
    echo Beende Testsystem ^(PID !PID!^) ...
    taskkill /PID !PID! /F >nul 2>&1
  )
  del /f /q "%PIDFILE%" >nul 2>&1
)

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo Beende Prozess auf Port 8000 ^(PID %%P^) ...
  taskkill /PID %%P /F >nul 2>&1
)

echo Testsystem gestoppt.
exit /b 0
