# Etape 2 - modulopdeling uden ændret funktionalitet

Status: Implementeret på udviklingsgrenen `codex/dashboard-3-foundation` den 17. oktober 2026 og afventer godkendelse. Senere etaper er ikke påbegyndt.

## Formål og metode

Den tidligere `app.py` rummede cirka 2.700 linjer med opstart, navigation, alle skærmbilleder, AI-kald, formatering, databasegateway og domænelogik. Koden er flyttet trinvist og i videst muligt omfang ordret. Der er ikke tilføjet nye forretningsfunktioner eller databasemigrationer.

Efter hvert hovedtrin blev samtlige navigationer renderet mod en kopi af den aktive database:

1. Først blev de eksisterende sideblokke flyttet til selvstændige visningsmoduler.
2. Derefter blev fælles kode opdelt i konfiguration, databasegateway, services og UI-hjælpere.
3. Til sidst blev imports gjort eksplicitte, testene udvidet og hele regressionstesten gentaget.

## Ny programstruktur

| Fil eller mappe | Ansvar |
| --- | --- |
| `app.py` | Streamlit-opstart, fælles layout, sidemenu og kald af valgt renderer. |
| `app_config.py` | Apptitel, navigation, aktørtyper og status-/typelister. |
| `app_context.py` | Lille, eksplicit facade med de afhængigheder, som visningsmodulerne må bruge. |
| `repositories.py` | Fælles gateway til `fetch_df` og `execute` samt enkelte delte opslag. |
| `views/` | Én renderfunktion for hver eksisterende navigation. |
| `services/ai_service.py` | Briefing- og mødeopfølgningsprompts, OpenAI-kald, lokalt fallback og samtykkekontrol. |
| `services/advisory_service.py` | Kildesynkronisering, mødekontekst, tidslinje og briefingkontekst. |
| `services/file_service.py` | Lokal lagring af uploadede dokumenter. |
| `ui/formatting.py` | Datoer, etiketter, tekstbehandling og opfølgningsgrupper. |
| `ui/navigation.py` | Streamlit session state for side-, profil- og opfølgningsnavigation. |
| `db.py` | Uændret ansvar for skema, migration, backup og lavniveau-databaseadgang. |
| `monitor.py` og `analysis_engine.py` | Eksisterende overvågnings- og signalanalysemoduler. |

`app.py` er reduceret til cirka 35 linjer. Den største resterende visning er virksomhedsprofilen på cirka 675 linjer; de øvrige visninger ligger mellem cirka 40 og 230 linjer.

## Flyttet kode

- Dashboard, opgaver, møder/referater, observationer, kontakter, viden, signalindbakke, virksomheder, briefing, kilder og triggerregler er flyttet uændret til `views/`.
- AI-funktionerne er flyttet fra `app.py` til `services/ai_service.py`. Standardværdien `allow_external=False` og den aktive samtykkeboks er bevaret.
- Tidslinje, mødefokus, briefingkontekst og automatisk oprettelse af aktørkilder er flyttet til `services/advisory_service.py`.
- Uploadlagring er flyttet til `services/file_service.py`.
- Formatering og Streamlit-navigation er flyttet til `ui/`.
- Databasekald fra visningerne går fortsat gennem de eksisterende `q`/`run`-funktioner, som nu ligger i `repositories.py`.
- Menunavne og eksisterende appnavn er samlet i `app_config.py` uden synlig ændring.

## Bevarede sikkerhedsforbedringer

- Versionsstyrede migrationer, backup før migration og restore-test er uændret.
- `Start Monitor.bat` binder fortsat kun til `127.0.0.1`.
- Dashboard-visning udfører fortsat ikke den tidligere utilsigtede kildesynkronisering.
- Mødereferater og briefingkontekst sendes ikke til OpenAI uden aktiv godkendelse ved den konkrete handling.
- Alle udviklings- og regressionstests anvender isolerede databaser eller `.stage2-test-data`.

## Gennemførte tests

Automatisk testsuite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultat: 10 tests gennemført, alle bestået.

Testene dækker:

- renderer for samtlige 11 navigationer;
- Dashboard og navigation uden Streamlit-undtagelser;
- aktør, kontaktperson, møde, referatdokument, briefing og opfølgning i samme relationelle workflow;
- ny database, migration af ældre database, integritet og fremmednøglekontrol;
- backup og isoleret gendannelsestest;
- lokal AI-fallback og standardmæssigt fravalg af eksternt AI-kald;
- ingen kildesynkronisering ved ren Dashboard-visning;
- lokal binding til `127.0.0.1`.

Alle Python-moduler er desuden kompileret med `compileall` uden fejl. Samtlige 11 visninger er særskilt renderet mod en kopi af den aktive database uden applikationsfejl. Den færdige Streamlit-app blev startet på `127.0.0.1:8513`, svarede HTTP 200 og blev derefter stoppet igen.

Databasekopien havde samme rækkeantal som den aktive database: 19 aktører, 6 kontakter, 1 møde, 3 opfølgninger, 4 briefinger, 36 signaler, 45 kilder og 5 triggerregler. Begge kontroller viste integritet `ok` og nul foreign-key-fejl. Før-migrationsbackuppen af kopien blev gendannet og kontrolleret med samme resultat.

## Aktiv database

Etape 2 indeholder ingen nye migrationer og har ikke ændret forretningsdata.

Under arbejdet den 17. oktober 2026 kl. 02.08.46 blev den aktive database imidlertid migreret med de allerede godkendte etape 1-migrationer i forbindelse med en lokal Streamlit-genindlæsning. Systemet oprettede først denne backup:

```text
monitor_pre_migration_20261017_020846_186741.db
```

Migrationen tilføjede tre rækker i `schema_migrations`. Alle forretningsmæssige rækkeantal var uændrede før og efter, integriteten er `ok`, og der er nul foreign-key-fejl. Den aktive database er dermed fysisk ændret siden etape 2-start, men kun med den godkendte etape 1-skemaændring; etape 2 har ikke ændret skema eller forretningsindhold.

Der foretages ikke en automatisk tilbagerulning, fordi den nuværende database er den tilsigtede etape 1-version, og en tilbagerulning ville være en unødig risiko for aktive data.

## Tilbageværende tekniske problemer

- `views/companies.py` er stadig relativt stor, fordi virksomhedens mange profilsektioner er bevaret samlet for ikke at ændre Streamlit-widgetnøgler og session state i denne etape.
- SQL-forespørgslerne er fortsat defineret tæt på de visninger, der bruger dem, selv om udførelsen går gennem `repositories.py`. De bør kun flyttes videre i forbindelse med en konkret fremtidig forretningsændring og tilhørende tests.
- Streamlit session state er fortsat den eksisterende navigationsmekanisme. Den er nu isoleret i `ui/navigation.py`, men ikke redesignet.
- Eksterne websites, feeds og faktiske OpenAI-kald er ikke udført i regressionstesten. De lokale kodeveje og sikkerhedsstandarder er testet.
- Tvungen foreign-key-håndhævelse er fortsat udskudt, indtil slettereglerne for relaterede poster er fastlagt.

## Samlet vurdering

De eksisterende centrale funktioner og alle navigationer fungerer fortsat i de gennemførte automatiske og lokale regressionstests. Koden er nu opdelt, så kommende arbejde med muligheder, tilbud og kundeopgaver kan afgrænses til nye services, repositories og visninger uden igen at udvide én samlet `app.py`.
