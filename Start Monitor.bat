@echo off
title Frank Advisory Intelligence Monitor
cd /d "%~dp0"

echo Starter Frank Advisory Intelligence Monitor...
echo Data gemmes i: %USERPROFILE%\FrankAdvisoryMonitorData
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :foundip
)
:foundip
set IP=%IP: =%

if "%IP%"=="" (
    set IP=localhost
)

echo PC:
echo http://localhost:8501
echo.
echo iPad / anden enhed paa samme netvaerk:
echo http://%IP%:8501
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Opretter Python-miljoe...
    py -3.12 -m venv .venv
)

echo Installerer/opdaterer pakker...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo Starter dashboard...
start http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --browser.serverAddress localhost --server.headless false

pause
