@echo off
title Backup Frank Advisory Monitor database

set DATA_DIR=%USERPROFILE%\FrankAdvisoryMonitorData
set BACKUP_DIR=%DATA_DIR%\Backups

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

if exist "%DATA_DIR%\monitor.db" (
    copy "%DATA_DIR%\monitor.db" "%BACKUP_DIR%\monitor_manual_backup.db"
    echo Backup oprettet i:
    echo %BACKUP_DIR%
) else (
    echo Ingen database fundet i %DATA_DIR%
)

pause
