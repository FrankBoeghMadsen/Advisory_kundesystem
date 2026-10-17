# Etape 1 - stabilt fundament og sikker database

Status: Afsluttet på udviklingsgrenen `codex/dashboard-3-foundation` den 17. oktober 2026. Etape 2-7 er ikke påbegyndt.

## Afgrænsning

Etapen ændrer ikke den grundlæggende Streamlit-arkitektur eller de eksisterende forretningsflows. Den tilføjer sikkerhed omkring database, lokal adgang og ekstern AI.

## Implementerede ændringer

- Tre versionsstyrede migrationer registreres i `schema_migrations`.
- En eksisterende database sikkerhedskopieres med SQLite backup-API før en ventende migration.
- Backups får tidsstemplede filnavne og kontrolleres med `PRAGMA integrity_check` og `PRAGMA foreign_key_check`.
- Migrationer køres enkeltvis i transaktioner og registreres først efter gennemført ændring.
- Databasen kontrolleres igen efter migration.
- SQLite-forbindelser lukkes eksplicit, og fremmednøgler kontrolleres efter migration og ved backupkontrol.
- `db_maintenance.py` kan oprette backup, kontrollere database og gennemføre isoleret gendannelsestest.
- `Backup database.bat` overskriver ikke længere den samme backupfil.
- Dashboard-visning opretter ikke længere manglende kilder som bivirkning. Kilder synkroniseres fortsat ved brugerens oprettelse eller redigering af en aktør.
- Mødeopfølgning og briefing sender som standard ingen data til OpenAI. Ekstern overførsel kræver et aktivt samtykke ved den konkrete generering.
- `Start Monitor.bat` binder Streamlit til `127.0.0.1` og installerer kun dependencies, hvis miljøet mangler dem.
- Der er tilføjet automatiske tests for database, migration, backup, gendannelse, relationer, AI-standardvalg, skrivefri Dashboard-visning og lokal netværksbinding.

## Test mod kopi af aktiv database

Den aktive database blev kopieret til projektets ignorerede `.stage1-test-data`-mappe. Alle migrations- og gendannelsestests blev udført på denne kopi.

Resultat før og efter migration:

| Tabel | Før | Efter |
| --- | ---: | ---: |
| `companies` | 19 | 19 |
| `contacts` | 6 | 6 |
| `meetings` | 1 | 1 |
| `followups` | 3 | 3 |
| `briefings` | 4 | 4 |
| `signals` | 36 | 36 |
| `sources` | 45 | 45 |
| `trigger_rules` | 5 | 5 |
| `company_cases` | 1 | 1 |
| `intelligence_memory` | 2 | 2 |
| `ignored_signal_rules` | 1 | 1 |
| Øvrige forretningstabeller | 0 | 0 |

Efter migration fandtes desuden tre rækker i `schema_migrations`. Integritetskontrollen var `ok`, og foreign-key-kontrollen fandt nul fejl.

Den automatisk oprettede før-migrationsbackup blev gendannet til en midlertidig testdatabase. Gendannelsen havde de oprindelige rækkeantal, integritet `ok` og nul foreign-key-fejl.

## Automatiske tests

Kør:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultat 17. oktober 2026: 7 tests gennemført, alle bestået.

Desuden er `app.py`, `db.py`, `db_maintenance.py` og `monitor.py` kompileret med `py_compile` uden fejl.

Streamlits testmotor åbnede følgende visninger mod den migrerede databasekopi uden applikationsfejl: Dashboard, Opgaver, Møder, Kontakter, Virksomheder og Briefing. En lokal testserver på `127.0.0.1:8513` svarede HTTP 200 og blev derefter lukket.

## Aktiv database

Etape 1 blev udviklet og testet mod en kopi. Den aktive database blev kun læst for at tage kopien og kontrollere metadata; den blev ikke migreret eller på anden måde ændret under udviklingen.

Før arbejdet:

- Fil: `%USERPROFILE%\FrankAdvisoryMonitorData\monitor.db`
- Størrelse: 323.584 byte
- Senest ændret: 1. juni 2026 kl. 17.29.14
- SHA-256: `06CA77F66EF054F81CB8A24C7EE10321CC500444BE25C3B15B490663C13BF6E2`

Ved aflevering blev størrelse, ændringstidspunkt og kontrolsum kontrolleret igen. Alle tre værdier var uændrede.

## Første start efter godkendelse

Når denne version senere startes mod den aktive database, sker følgende automatisk:

1. Der registreres, at migration 1-3 mangler.
2. Der oprettes en tidsstemplet `monitor_pre_migration_*.db` i `Backups`.
3. Backuppen integritetskontrolleres.
4. Migrationerne køres og registreres.
5. Den migrerede database integritetskontrolleres.

Ingen eksisterende forretningsrækker slettes eller omnummereres af migrationerne.

## Rollback og manuel gendannelse

Ved rollback skal appen først stoppes. Bevar altid den aktuelle database som en ekstra fil, før en backup kopieres tilbage.

1. Skift programkoden tilbage til den tidligere fungerende Git-version eller grenen `main`.
2. Find den relevante `monitor_pre_migration_*.db` i `%USERPROFILE%\FrankAdvisoryMonitorData\Backups`.
3. Kør `db_maintenance.py restore-check` på backupfilen.
4. Omdøb den aktuelle `monitor.db` til en tidsstemplet fejl-/kontrolkopi.
5. Kopiér den verificerede backup tilbage som `monitor.db`.
6. Start den tidligere programversion og kontroller aktører, møder, opfølgninger og briefings.

Selve tilbagekopieringen er bevidst ikke automatiseret, fordi en forkert sti ellers kan overskrive den aktive database.

## Kendte afgrænsninger

- Der er ikke foretaget eksterne OpenAI-kald eller live-kald til websites/feeds i testen.
- AI-samtykket gælder den konkrete generering. Mere detaljeret klassifikation og redaktion af enkelte fortrolige felter hører til en senere, særskilt godkendt etape.
- Hosting og iPad-adgang uden tændt PC er ikke implementeret.
- Den større modulopdeling af `app.py` er ikke påbegyndt.
- Tvungen SQLite-fremmednøglehåndhævelse er ikke aktiveret endnu. Det kræver først dokumenterede sletteregler for eksisterende møder, kilder og andre poster, så nuværende slettefunktioner ikke brydes.
