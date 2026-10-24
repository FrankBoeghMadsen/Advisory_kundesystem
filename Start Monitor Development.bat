@echo off
title FBM Advisory Dashboard - UDVIKLING
cd /d "%~dp0"

set "FRANK_MONITOR_MODE=development"
set "FRANK_MONITOR_PLANNING_MIGRATION=1"
set "FRANK_MONITOR_STAGE52_MIGRATION=1"
set "FRANK_MONITOR_STAGE61_MIGRATION=1"
set "FRANK_MONITOR_PRODUCTION_DATA_DIR=%USERPROFILE%\FrankAdvisoryMonitorData"
set "FRANK_MONITOR_DATA_DIR=%~dp0.dev-data"

echo Starter UDVIKLINGSVERSIONEN...
echo Data gemmes isoleret i: %FRANK_MONITOR_DATA_DIR%
echo Aktiv database aabnes ikke.
echo.
echo Lokal adresse: http://127.0.0.1:8502
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Python-miljoe mangler. Start den almindelige version foerst.
    pause
    exit /b 1
)

start http://127.0.0.1:8502
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --browser.serverAddress 127.0.0.1 --server.port 8502 --server.headless false

pause
