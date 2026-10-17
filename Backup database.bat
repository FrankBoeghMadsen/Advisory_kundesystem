@echo off
title Backup FBM Advisory Dashboard
cd /d "%~dp0"

set "FRANK_MONITOR_MODE=production"
set "FRANK_MONITOR_PRODUCTION_DATA_DIR=%USERPROFILE%\FrankAdvisoryMonitorData"
set "FRANK_MONITOR_DATA_DIR=%USERPROFILE%\FrankAdvisoryMonitorData"

if not exist ".venv\Scripts\python.exe" (
    echo Python-miljoet mangler. Start foerst programmet med Start Monitor.bat.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" db_maintenance.py backup --label manual
if errorlevel 1 echo Backup blev ikke oprettet. Se fejlmeddelelsen ovenfor.

pause
