@echo off
title Backup Frank Advisory Monitor database
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python-miljoet mangler. Start foerst programmet med Start Monitor.bat.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" db_maintenance.py backup --label manual
if errorlevel 1 echo Backup blev ikke oprettet. Se fejlmeddelelsen ovenfor.

pause
