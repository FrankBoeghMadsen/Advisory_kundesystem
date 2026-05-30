# Windows setup

Denne app er testet som lokal Streamlit-app med Python 3.12.

## 1. Gå til projektmappen

```powershell
cd "C:\Users\frank\Documents\Codex\2026-05-30\kan-du-finde-vores-l-ngerevarende\frank_advisory_monitor_v2_4"
```

## 2. Opret virtuelt Python-miljø

Hvis `python` ikke findes i PATH, brug den fulde Python 3.12-sti:

```powershell
C:\Users\frank\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv
```

## 3. Aktiver miljøet

```powershell
.\.venv\Scripts\Activate.ps1
```

Hvis PowerShell blokerer aktivering:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Aktiver derefter miljøet igen.

## 4. Installer dependencies

```powershell
python -m pip install -r requirements.txt
```

## 5. Start appen

```powershell
streamlit run app.py
```

## iPad på samme netværk

Når appen kører lokalt på PC'en, kan den normalt åbnes fra en iPad på samme Wi-Fi via PC'ens lokale IP-adresse og Streamlit-porten, typisk:

```text
http://PC_LOCAL_IP:8501
```

Brug `Start Monitor.bat`, som viser både PC-adressen og iPad-adressen. Hvis iPad ikke kan forbinde, skyldes det typisk Windows Firewall eller at PC og iPad ikke er på samme netværk.
