# FBM Advisory Dashboard

Seneste godkendte brugerforbedring: [leveranceformular, acceptdokumentation og enkel ugeplan](BRUGERFORBEDRINGER_UGEPLAN.md). Kræver migration 9 på den isolerede udviklingsdatabase og genstart via `Start Monitor Development.bat`, med backup før migration. Ingen driftsoverførsel eller Outlook-integration.

Etape 6.1b samler projektknapper ved overskrifterne, forbedrer formularhandlinger og retur-navigation og gør tilknytningsvejledning situationsbestemt. Se [ændringer, testresultater, begrænsninger og prøvevejledning](ETAPE_6_1B_IMPLEMENTERING.md). Ingen migration eller driftsoverførsel.

Etape 6.1a forbedrer projektoversigt, formularnulstilling, aktive valg, kvitteringer og navigation tilbage fra forløb. Se [ændringer, tests og prøvevejledning](ETAPE_6_1A_IMPLEMENTERING.md). Ingen ny migration; drift er fortsat ikke frigivet.

Etape 6.1 tilføjer en valgfri projektkerne under Forretning → Projekter. Se [implementering, migration og prøvevejledning](ETAPE_6_1_IMPLEMENTERING.md). Eksisterende enkeltkundeopgaver kræver fortsat intet projekt. Økonomimodel og funktioner fra 6.2–6.6 er ikke implementeret; drift er ikke frigivet.

Seneste begrænsede forbedring: [Etape 5.2](ETAPE_5_2_IMPLEMENTERING.md), afslutning med resultat og dato, valgfrie opfølgningskoblinger og diskrete statusfiltre. [Plan for ren drift og de første kunder](ETAPE_5_2_DRIFTSPLAN.md) er alene analyse. En kørende udviklingssession skal genstartes via `Start Monitor Development.bat` før migration 7; automatisk genindlæsning er spærret. Drift er ikke frigivet.

Aktuel udviklingsversion: 3.0. Se [ETAPE_5_1_IMPLEMENTERING.md](ETAPE_5_1_IMPLEMENTERING.md) for møder, selvstændige opfølgninger, sikker sletning, testresultater, prøvevejledning og planen for senere ren drift. Det øvrige aktivitetsoverblik er beskrevet i [ETAPE_5_IMPLEMENTERING.md](ETAPE_5_IMPLEMENTERING.md).

Udviklingsversionen er endnu ikke frigivet til drift. Den aktuelle kode afprøves med `Start Monitor Development.bat`; produktionstilstand stopper, hvis udviklingsmigrationerne afventer. Den aktive database opgraderes først efter særskilt godkendelse.

En første fungerende MVP som lokal Streamlit-webapp til passiv overvågning af danske life science-virksomheder.

## Hvad den kan
- Oprette/redigere virksomheder, kilder, triggerregler, kontaktpersoner og noter
- Køre manuel overvågning via konfigurerbare kilder
- Indsamle fund fra RSS/nyhedsfeeds og simple web-kilder
- Score fund som Lav/Middel/Høj/Kritisk
- Markere myndighedsreaktioner og andre relevante signaler
- Vise dashboard, signalindbakke, virksomhedsprofiler og noter
- Håndtere forretningsforløb, tilbud, kundeopgaver, leverancer og deadlines
- Eksportere signaler til CSV
- Bruge OpenAI til opsummering/scoring, hvis `OPENAI_API_KEY` sættes og den konkrete overførsel godkendes; ellers bruges lokal eller regelbaseret analyse

## Kom hurtigt i gang

På Windows startes den aktive version med `Start Monitor.bat`. Startfilen vælger eksplicit driftstilstand, den aktive datamappe og lokal binding til `127.0.0.1`.

Udviklingsversionen startes kun med `Start Monitor Development.bat`. Den bruger den isolerede, Git-ignorerede mappe `.dev-data` og port 8502.

Direkte `streamlit run app.py` uden en eksplicit driftstilstand stopper af sikkerhedshensyn, før en database åbnes.

Første gang appen startes, oprettes en lokal SQLite-database med virksomhederne fra masterlisten.

## Valgfri AI-analyse

Opret en `.env`-fil:

```bash
OPENAI_API_KEY=din_api_noegle
OPENAI_MODEL=gpt-4.1-mini
```

Uden nøgle virker appen stadig med lokal og regelbaseret analyse. En API-nøgle er ikke i sig selv nok til at sende møde- eller briefingdata til OpenAI. Det kræver et aktivt valg ved hver generering.

## Data og backup

Den aktive database ligger i:

```text
%USERPROFILE%\FrankAdvisoryMonitorData\monitor.db
```

Programmet har en fail-closed databaseafskærmning:

- Drift må kun skrive i den aktive datamappe.
- Udvikling og test afvises, hvis de peger på den aktive datamappe eller en undermappe i den.
- Automatiske tests bruger altid midlertidige databaser under projektets testområde.

Ved en ny databasemigration oprettes først en verificeret backup i `Backups`. `Backup database.bat` opretter en særskilt tidsstemplet manuel backup og overskriver ikke tidligere filer.

Databasekontrol og en isoleret gendannelsestest kan køres med:

```powershell
.\.venv\Scripts\python.exe db_maintenance.py verify "$env:USERPROFILE\FrankAdvisoryMonitorData\monitor.db"
.\.venv\Scripts\python.exe db_maintenance.py restore-check "C:\sti\til\backup.db"
```

Se [ETAPE_1_STABILISERING.md](ETAPE_1_STABILISERING.md) for migrationer, testresultater og rollback.

## Programstruktur

Brugerfladen er opdelt uden ændring af navigationen:

- `app.py`: opstart, fælles layout og navigation.
- `views/`: én renderfunktion pr. eksisterende visning.
- `services/`: AI, aktør-/briefinglogik og lokal dokumentlagring.
- `services/business_service.py`: kontrollerede overgange og koblinger i forretningsmodulet.
- `repositories.py`: fælles gateway til databaseforespørgsler og skrivehandlinger.
- `ui/`: formatering og navigationstilstand.
- `app_config.py`: fælles navne, sidemenuer og statuslister.
- `db.py`: skema, migrationer, backup og lavniveau-databaseadgang.
- `runtime_config.py`: fail-closed valg af drift, udvikling og testdatabase.

Se [ETAPE_2_MODULOPDELING.md](ETAPE_2_MODULOPDELING.md) for flyttede kodeområder, regressionstest og kendte afgrænsninger.

Se [ETAPE_3_FORRETNINGSMODUL_DESIGN.md](ETAPE_3_FORRETNINGSMODUL_DESIGN.md) og [ETAPE_3_IMPLEMENTERING.md](ETAPE_3_IMPLEMENTERING.md) for datamodel, databaseisolering, arbejdsgange og testresultater for forretningsmodulet.

## Bemærk
Denne MVP bruger kun konfigurerbare offentlige feeds/web-kilder. LinkedIn er ikke automatiseret.

## Begrebet "virksomhed"

I den nuværende datamodel hedder den centrale aktør stadig `virksomhed`. I praksis kan den også bruges til brancheforeninger, vigtige relationer, rådgivere, kaffemødekontakter eller andre aktører, som Frank Advisory ønsker at følge over tid.

Profiler kan nu markeres med en særskilt aktørtype, fx life science-virksomhed, apotek, brancheforening, person/relation, myndighed eller rådgiver/partner. Det gør det muligt at bruge samme profilvisning bredere uden at splitte systemet op for tidligt.

En senere version bør overveje at omdøbe dette til `aktør`, `relation` eller `kundeemne`, så systemet ikke kun er bundet til klassiske life science-virksomheder.

## Nyt i v1.1
- Virksomheder kan sættes til Aktiv, Pauset eller Arkiveret
- Overvågningen medtager kun virksomheder med status Aktiv
- Website og LinkedIn kan opdateres fra brugerfladen
- Aliaser kan tilføjes pr. virksomhed, fx `Novo|Novo Nordisk`
- Virksomhedslisten har separat redigeringspanel


## Nyt i v1.2
- Startfiler til Windows:
  - Start Monitor - PC.bat
  - Start Monitor - iPad.bat
- Separat datamappe:
  - %USERPROFILE%\FrankAdvisoryMonitorData
- Automatisk kopiering af eksisterende lokal database første gang v1.2 startes
- Automatisk daglig backup af databasen
- Manuel backupfil: Backup database.bat
- Virksomhedens navn/titel kan redigeres fra virksomhedsvisningen

## Fremover
Når data først ligger i FrankAdvisoryMonitorData, kan nye programversioner installeres uden at overskrive dine data.


## Nyt i v2.0

Dette er første reelle version af intelligence-laget.

Nyt:
- Virksomhedsprofiler som ny central visning
- Historik/sager pr. virksomhed
- Kilder/links kan samles under samme sag
- Intelligence memory pr. virksomhed
- Kontakter vises og oprettes fra virksomhedsprofilen
- Signaler vises under virksomheden med uddrag/resume
- Kildeadministration: redigér, aktivér, pausér/arkivér og slet kilder
- Cases/sager kan bruges til historiske forløb som fx Scanpharm 2019-2020
- Bevarer ekstern datamappe og backup fra v1.2

## Opgradering fra v1.2

Hvis du allerede bruger v1.2, skal du normalt bare pakke v2.0 ud og starte den.
Data ligger i:

%USERPROFILE%\FrankAdvisoryMonitorData

v2.0 migrerer databasen automatisk med nye tabeller.

## Nyt i v2.1

- Dashboard er ryddet op og viser nu overblik/arbejdsliste.
- Signalindbakken er nu stedet, hvor signaler behandles.
- Signaler kan markeres som: Ny, Til vurdering, Gemt på virksomhed, Irrelevant eller Arkiveret.
- Signaler får kildeuddrag, hvor systemet kan hente relevant tekst fra kilden.
- Systemet viser matchende ord/termer, hvis de kan findes.
- Virksomhedsvisningen har både oversigt og virksomhedsprofil.
- Kategori-feltet er gjort større ved redigering.
- Noter og Historik/Sager ligger nu kun under virksomheden.
- Startfilen til iPad viser nu den rigtige lokale IP-adresse.
- PC-startfilen åbner browseren automatisk.

## Rettelse i v2.2.1
- Retter SyntaxError i db.py fra v2.2.
- Bevarer v2.2-funktioner: møder, observationer, referat-upload, briefing og ny datamodel.

## Nyt i v2.2.2
- Én samlet startfil: `Start Monitor.bat`
- Startfilen viser både PC-adressen og den rigtige iPad-adresse.
- Browseren åbner nu på `localhost` på PC'en, ikke 0.0.0.0.
- Datoer i centrale memory-visninger vises mere læsevenligt som dag-måned-år.
- Samme signal fra samme kilde genindlæses ikke igen, fordi systemet gemmer signalets unikke nøgle. Samme hændelse fra andre kilder kan dog stadig dukke op og skal senere håndteres med event-clustering.

## Nyt i v2.2.3
- Virksomhedsoversigten har nu Åbn profil-knapper.
- Virksomhedsprofilen husker valgt virksomhed.
- Faneblade viser antal registrerede oplysninger, fx Kontakter (2) og Intelligence memory (3).
- Oversigten viser badges for, hvor der findes data.
- Kontakter kan nu redigeres og slettes.
- Ny stabilisering mod det advisory-intelligence workflow, hvor virksomhedsprofilen er centrum.

## Nyt i v2.2.4
- Noter har nu overskrift/titel.
- Nyt notefelt starter tomt.
- Noter kan redigeres og slettes, hvor note-sektionen kunne patches direkte.
- Datoer i note-/memoryvisninger er gjort mere læsevenlige.
- Fremtidigt UI-spor: mere grafisk, mindre databasepræget og med små ikonknapper til redigering/sletning.

Teknisk note: notes_patch=False

## Nyt i v2.2.5
- Dashboard er gjort mere enkelt og handlingsorienteret.
- Virksomhedsoversigten er tættere, så flere virksomheder kan ses.
- Fanen "Intelligence memory" hedder nu "Videnbank".
- Datoer og tekniske felter er gjort mere danske/læsevenlige.
- Signaler kan arkiveres eller slettes fra virksomhedsprofilen.
- Sager/historik kan redigeres og slettes.
- Møder, observationer, kontakter, noter og videnbank har redigér/slet-funktion.
- Nye formularer nulstilles bedre efter gem.
- Noter har overskrift.

## Nyt i v2.2.6
- Dashboard-knap går nu reelt til Signalindbakke.
- Virksomhedsoversigten har Åbn-knappen tæt på virksomhedsnavnet.
- Profilvisningen bruger radiovalg frem for tabs, så den bedre bliver på samme sektion efter ændringer.
- Møder har nu tidspunkt og adresse/sted.
- Dashboard viser kommende møder/husketing.
- Upload-referat bruger nye nøgler efter gem, så gamle data ikke bliver hængende på samme måde.
- Historik/sager, noter, observationer, kontakter og videnbank har fortsat redigér/slet-flow.
- Kilder og triggerregler er midlertidigt gjort til renere oversigtsvisninger, så mærkelige redigeringsdata ikke fylder.

## Stabiliseringsrettelser i v2.2.7
- Retter fejl ved Åbn-knap i virksomhedsoversigten.
- Retter DeltaGenerator-fejl på Møder, Kilder og Triggerregler.
- Fjerner Observationer som selvstændigt menupunkt; observationer ligger under virksomheden.
- Dashboardets mødebriefingtekst er gjort mere meningsfuld.
- Dashboard har genvej til Briefing.
- Ingen nye større funktioner; denne version er primært stabilisering.

## Nyt i v2.3
- Dashboard viser aktuel dato.
- Møder & referater er fjernet som selvstændigt menupunkt; møder hører under virksomhedsprofil og Briefing.
- Kontakter vises tættere.
- Briefing har første AI-/lokal generator, der samler data på tværs af møder, observationer, sager, signaler, noter og videnbank.
- Fokus er nu mødeforberedelse frem for flere selvstændige oversigter.


## Nyt i v2.4
- AI-briefing via OpenAI Responses API.
- Tydelig fejlbesked hvis API-kald fejler.
- Lokal fallback hvis API-nøgle mangler.
- Redigér/slet for Kilder.
- Redigér/slet for Triggerregler.

### Sådan aktiveres AI
1. Opret OpenAI API-nøgle.
2. Åbn CMD eller PowerShell.
3. Kør:

setx OPENAI_API_KEY "din_api_nøgle"

4. Luk terminal/program og start monitoren igen.
