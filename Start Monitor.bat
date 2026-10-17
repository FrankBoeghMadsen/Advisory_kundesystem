@echo off
title Frank Advisory Intelligence Monitor
cd /d "%~dp0"

echo Starter Frank Advisory Intelligence Monitor...
echo Data gemmes i: %USERPROFILE%\FrankAdvisoryMonitorData
echo.
echo Lokal adresse: http://127.0.0.1:8501
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Opretter Python-miljoe...
    py -3.12 -m venv .venv
    echo Installerer pakker foerste gang...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\python.exe" -c "import streamlit, pandas, requests, bs4, feedparser, dotenv, openai, docx, pypdf" >nul 2>&1
if errorlevel 1 (
    echo Nødvendige pakker mangler. Installerer fra requirements.txt...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo Starter dashboard...
start http://127.0.0.1:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --browser.serverAddress 127.0.0.1 --server.headless false

pause
