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
streamlit run app.py --server.address 127.0.0.1
```

Du kan også bruge `Start Monitor.bat`. Den binder som standard kun appen til `127.0.0.1`, så andre enheder på netværket ikke kan åbne den.

## Opdater dependencies

Startfilen installerer ikke længere pakker ved hver start. Hvis `requirements.txt` ændres, køres:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Backup og kontrol

Kør `Backup database.bat` for en tidsstemplet og integritetskontrolleret manuel backup. Tidligere manuelle backups overskrives ikke.

En database kan kontrolleres uden at ændre den:

```powershell
.\.venv\Scripts\python.exe db_maintenance.py verify "$env:USERPROFILE\FrankAdvisoryMonitorData\monitor.db"
```

En backup kan prøvegengendannes i en midlertidig mappe uden at ændre den aktive database:

```powershell
.\.venv\Scripts\python.exe db_maintenance.py restore-check "C:\sti\til\backup.db"
```

## iPad og fjernadgang

Fjernadgang er ikke aktiveret i etape 1. Sikker adgang fra iPad uden en tændt PC kræver senere en særskilt hosting-, login- og backupbeslutning. Appen bør ikke eksponeres direkte på internettet.
