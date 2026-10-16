# Frank Advisory Dashboard 3.0 – Udviklingsplan

**Fase:** 1 – teknisk og funktionel analyse  
**Dato:** 17. oktober 2026  
**Status:** Klar til ejerens godkendelse. Ingen implementering er påbegyndt.

## 1. Samlet anbefaling

Frank Advisory Intelligence Monitor har udviklet sig fra en overvågnings-MVP til et anvendeligt personligt arbejdsredskab med aktører, kontakter, møder, referater, opfølgninger, briefinger, signaler og historik. Den nuværende løsning indeholder allerede en stor del af det fundament, som Frank Advisory Dashboard 3.0 har brug for.

Den anbefalede retning er:

1. Brug den aktuelle Git-branch `main` som teknisk udgangspunkt. ZIP-version 2.5.3 er historisk reference og bør ikke bruges som ny base.
2. Behold Streamlit og SQLite i version 3.0. De passer til en enkelt bruger, den aktuelle datamængde og behovet for hurtig, pragmatisk udvikling.
3. Stabiliser og opdel den nuværende kode, før der tilføjes større funktioner. `app.py` er blevet en monolit og er den største regressionsrisiko.
4. Indfør ét enkelt forretningsmodul for muligheder, tilbud og kundeopgaver. Undgå at bygge et fuldt CRM- eller ERP-system.
5. Lad dashboardet blive en handlingsside baseret på opgaver, møder, tilbud, leverancer og relevante signaler – ikke en samling generelle tællere.
6. Genbrug eksisterende data og funktioner. Segmenteringsarket bør importeres kontrolleret med forhåndsvisning og dubletkontrol, ikke kopieres manuelt felt for felt.
7. Bevar AI som valgfri funktion. Fortrolige oplysninger må kun sendes til en ekstern AI-tjeneste efter en tydelig brugerhandling og med synlig information om, hvad der sendes.
8. Udskyd større teknologiskift og internet-hosting, til det reelle behov for iPad-adgang uden tændt PC er afklaret.

Den vigtigste nye funktion er ikke mere overvågning. Det er et enkelt, sammenhængende forløb fra relation og mulighed til tilbud, kundeopgave, leverance og afslutning.

## 2. Gennemgået materiale og afgrænsning

Analysen er baseret på:

- Den aktuelle Git-kodebase på `main`, seneste commit ved gennemgangen: `54151da Add knowledge workspace`.
- ZIP-filen `frank_advisory_monitor_v2_5_3.zip` som historisk versionsreference.
- Den aktive database `FrankAdvisoryMonitorData/monitor.db`, åbnet read-only.
- Segmenteringsarket `segmenteringsark_frank_bøgh_madsen_advisory.xlsx`, åbnet read-only.
- README, versionsnoter, start- og backupfiler samt Python-modulerne i projektet.

I fase 1 er der:

- ikke ændret data i databasen;
- ikke foretaget API-kald eller scraping;
- ikke installeret nye projektafhængigheder;
- ikke ændret programkode;
- ikke importeret data fra segmenteringsarket.

## 3. Teknisk status

### 3.1 Nuværende opbygning

Løsningen består af følgende hoveddele:

| Komponent | Ansvar | Status |
|---|---|---|
| `app.py` | Hele Streamlit-brugerfladen, navigation, formularer, SQL-kald, AI-prompts og arbejdsflows | Funktionel, men for stor og tæt koblet |
| `db.py` | SQLite-skema, forbindelser, simple migrationer, seed-data og backup | Enkel og brugbar, men uden versionsstyrede migrationer |
| `monitor.py` | Kørsel af kilder, match til aktør og lagring af signaler | Fungerende basis |
| `connectors.py` | RSS- og simple webkilder samt tekstuddrag | Begrænset, men klart afgrænset |
| `analysis_engine.py` | Regelbaseret signalvurdering og valgfri OpenAI-vurdering | Fungerende med lokal fallback |
| `document_utils.py` | Tekstudtræk fra TXT, DOCX og PDF samt simpel mødeopsummering | Fungerende basis |
| `Start Monitor.bat` | Opretter miljø, installerer pakker og starter Streamlit | Praktisk, men gør for meget ved hver start |
| `Backup database.bat` | Manuel kopi af databasen | Enkel, men overskriver samme manuelle backup |

`app.py` er cirka 2.500 linjer og rummer både præsentation, state management, SQL, forretningslogik og AI-logik. De øvrige moduler er relativt små og mere afgrænsede. Det betyder, at den væsentligste tekniske gæld ikke er teknologivalget, men koncentrationen af ansvar i én fil.

### 3.2 Versionsstatus

ZIP-version 2.5.3 indeholder den tidligere hotfixgren med briefinger og tidslinje. Den aktuelle Git-version er væsentligt videreudviklet og indeholder blandt andet:

- handlingsorienteret dashboard;
- tværgående opgave-/leadside;
- tværgående mødeside;
- sammenlægning af mødeposter;
- tværgående observationer;
- tværgående kontakter;
- tværgående viden/noter;
- aktørtyper;
- forbedret profilnavigation;
- gemte briefinger og AI-opfølgning;
- synkronisering af aktørlinks til kilder.

Konsekvensen er, at 2.5.3 ikke bør geninstalleres oven på den aktuelle løsning. Den bør kun bevares som historisk dokumentation.

### 3.3 Funktionel modenhed

| Område | Vurdering | Bemærkning |
|---|---|---|
| Aktørregister | Godt fungerende | Understøtter virksomhed, apotek, brancheforening, person/relation m.fl. Den fysiske tabel hedder fortsat `companies`. |
| Aktørprofil og tidslinje | Godt fungerende | Samler møder, opfølgninger, signaler, observationer, sager, noter, viden og briefinger. |
| Kontakter | Godt fungerende basis | Telefon, email, LinkedIn, rolle og noter findes. Relationens styrke og seneste kontakt er ikke struktureret. |
| Møder og referater | Godt fungerende basis | Oprettelse, upload, tekstudtræk, redigering og sammenlægning findes. Dokumentregistreringen er ikke fuldt koblet til databasens dokumenttabel. |
| Opgaver og opfølgninger | Delvist færdigt | God arbejdsvisning, status og deadlines. Modellen blander lead, opfølgning, relation og intern opgave. |
| Tilbud og kundeopgaver | Mangler | Der findes ingen særskilt livscyklus, honorar, leverancer eller tilbudsstatus. |
| Dashboard | Delvist færdigt | Handlingsorienteret, men kan endnu ikke vise aktive kundeopgaver og tilbud som selvstændige forretningsobjekter. |
| Segmentering | Delvist færdigt | Prioritet og aktørtype findes, men de fleste felter fra segmenteringsarket mangler i databasen. |
| Signalindbakke | Fungerende basis | Signaler kan vurderes og arkiveres. Relevansfiltreringen er for bred. |
| Intelligence Monitor | Delvist færdigt | RSS og simple websider virker. Match sker primært via navne/aliaser og kan give støj. LinkedIn er en manuel referencekilde. |
| AI-briefing | Godt fungerende basis | Valgfrit API-kald, lokal fallback, gemte briefinger og mødeopfølgning findes. Fortrolighedsstyringen er utilstrækkelig. |
| Dokumenthåndtering | Delvist implementeret | Filer gemmes lokalt og tekst udtrækkes, men `uploaded_documents` bruges ikke konsekvent. |
| Backup | Fungerende basis | Ekstern datamappe og daglige kopier findes. Gendannelse, retention og validering mangler. |
| Test og kvalitetssikring | Problemområde | Der findes ingen projektspecifik automatiseret testsuite eller CI-konfiguration. |

### 3.4 Aktuel database

Databasen er lille og egnet til SQLite:

| Datatype | Antal ved gennemgangen |
|---|---:|
| Aktører | 19 |
| Kontakter | 6 |
| Møder | 1 |
| Opfølgninger/opgaver | 3 |
| Briefinger | 4 |
| Videnbank-punkter | 2 |
| Signaler | 36 |
| Kilder | 45 |
| Triggerregler | 5 |

Databasens `PRAGMA integrity_check` returnerede `ok`, og `foreign_key_check` fandt ingen aktuelle brud.

Der er dog følgende tekniske forhold:

- Koden aktiverer ikke `PRAGMA foreign_keys=ON` på forbindelser. De deklarerede relationer håndhæves derfor normalt ikke af SQLite.
- Der findes ikke en `schema_migrations`-tabel eller et egentligt migrationsnummer. Migrationer udføres som gentagne `ALTER TABLE`-kontroller ved start.
- Den aktive database indeholder ældre felter og tabellen `ignored_signal_rules`, som ikke er fuldt deklareret i den aktuelle kildekode. Det er tegn på skemadrift mellem versioner.
- Der er næsten ingen indekser ud over automatiske unikke indekser. Det er ikke et ydelsesproblem med den aktuelle datamængde, men bør håndteres ved nye forretningstabeller.
- Flere statusværdier er fritekst eller defineret forskellige steder. Eksempelvis indeholder briefinger både `Aktiv` og `Kladde`, mens dele af brugerfladen anvender andre valgmuligheder.
- Datoer gemmes som tekst og valideres kun begrænset.
- Flertrinsoperationer, eksempelvis sammenlægning af møder, udføres som flere separate commits og er ikke atomiske.

### 3.5 Backup og filer

Data ligger korrekt uden for kodebasen i `FrankAdvisoryMonitorData`. Det er en vigtig og velfungerende beslutning, fordi programkoden kan opdateres uden at overskrive databasen.

Der findes daterede backupfiler fra maj, juni og oktober 2026. Den automatiske backup oprettes ved dagens første programstart, hvis dagens fil ikke allerede findes.

Styrker:

- database og kode er adskilt;
- der findes både automatisk og manuel backup;
- backupfilerne ligger i en tydelig mappe;
- den aktuelle database er integritetsmæssigt i orden.

Svagheder:

- backup tages efter skemaændringer ved programstart, ikke før migrationen;
- kopiering sker som en almindelig filkopi og ikke via SQLite Backup API;
- den manuelle backup overskriver filen `monitor_manual_backup.db`;
- der findes ingen automatisk retention, ekstern kopi eller dokumenteret restore-test;
- databasen og dokumenterne sikkerhedskopieres ikke som én samlet, konsistent pakke;
- der findes en fysisk uploadet DOCX-fil, mens `uploaded_documents`-tabellen er tom. Den nuværende uploadfunktion gemmer fil og mødetekst, men opretter ikke dokumentposten.

Før databaseændringer i 3.0 bør backupflowet ændres til: backup før migration, integritetskontrol, migration i transaktion og dokumenteret gendannelsestest.

### 3.6 Segmenteringsarket

Segmenteringsarket indeholder 18 reelle virksomheder i masterlisten og 7 i den prioriterede shortlist. De vigtigste strukturerede felter er:

- segment og tilladelsesspor;
- overordnet kategori;
- hvorfor aktøren er relevant;
- mulig indgang;
- relationstyrke;
- købspotentiale;
- følsomhed ved standsning;
- prioritet og samlet score;
- status, fase og næste skridt;
- sandsynlig intern køber og kernefortælling.

Seks aktører er markeret i fase 1, elleve i fase 2 og én i fase 3. Tolv af de atten masterlisteposter mangler et udfyldt næste skridt. Shortlisten har fem `Høj A`- og to `Høj B`-aktører.

Der er 17 eksakte navnematches mellem database og masterliste. Den eneste navnevariation er `ALK-Abelló A/S` mod `ALK-Abello A/S`. `Apotekerforeningen` findes i databasen og shortlisten, men ikke i masterlisten. Det viser, at en import er realistisk, men skal have normalisering og manuel dubletgodkendelse.

Anbefaling: Dashboard 3.0 skal på sigt være den primære kilde til aktive prioriteter. Excel-arket bør bruges som kontrolleret importkilde og derefter som arkiv/reference, så de samme oplysninger ikke vedligeholdes to steder.

### 3.7 Signalernes kvalitet

Af de 36 gemte signaler er:

- 27 markeret irrelevante;
- 5 arkiveret;
- 4 gemt på en aktør;
- 0 står som nye ved gennemgangen.

En irrelevansandel på 75 % viser, at overvågningen teknisk virker, men at match og prioritering er for bred. Næste investering bør derfor være bedre målretning mod aktuelle kunder, tilbud, rådgivningsområder og højprioriterede aktører – ikke flere kilder eller mere scraping.

### 3.8 Teknisk gæld og risici

De væsentligste punkter er:

1. **Monolitisk brugerflade.** `app.py` samler næsten alle ansvar og gør små ændringer risikable.
2. **SQL direkte i UI-koden.** Forretningsregler og dataadgang kan ikke testes isoleret.
3. **Ingen automatiserede tests.** Der er ingen projektspecifik testsuite for database, navigation, statusflow eller centrale workflows.
4. **Ingen versionsstyrede migrationer.** Skemadrift kan allerede ses i den aktive database.
5. **State management er manuelt.** Mange widgetnøgler og `session_state`-ændringer har tidligere givet regressionsfejl.
6. **Uventede skrivehandlinger.** Dashboardvisning kan synkronisere aktørlinks til kildetabellen blot ved at åbne siden.
7. **Manglende transaktioner.** Sammensatte operationer kan ende halvt gennemført ved fejl.
8. **Stale dokumentation.** Titel og README omtaler fortsat v2.4, selv om funktionaliteten er videreudviklet.
9. **Installation ved hver start.** Startfilen kører `pip install` hver gang, hvilket giver unødig ventetid og risiko for miljøændringer.
10. **Blandet domænemodel.** `followups` bruges til både lead, opgave, relation, kundeforløb og mødeopfølgning.

### 3.9 Sikkerhed og fortrolighed

Positive forhold:

- API-nøglen er ikke hardkodet og `.env` er ignoreret af Git.
- AI er valgfri og har lokal fallback.
- databasefiler og uploads er ignoreret af Git.
- filnavne renses for skråstreger før lagring.

Risici, som skal håndteres:

- Streamlit startes på `0.0.0.0` uden login og TLS. Alle på samme lokale netværk kan potentielt åbne appen, hvis netværk/firewall tillader det.
- Database og uploadede dokumenter ligger ukrypteret på disken. Windows-konto, disk-kryptering og backupadgang bliver derfor en del af sikkerheden.
- AI-briefing kan sende møder, noter, sager, relationer og opfølgninger til OpenAI, når en API-nøgle er sat. Der er ingen eksplicit forhåndsvisning, redaktion eller fortrolighedsregel pr. post.
- Fejlmeddelelser fra API kan vises direkte og kan indeholde tekniske detaljer.
- Upload begrænser filendelser, men ikke filstørrelse eller reelt MIME-indhold.
- Sletning sker ofte uden ekstra bekræftelse eller soft-delete.
- En senere cloudversion kræver autentifikation, TLS, secret management, databehandlerafklaring, adgangslog og krypteret backup. Den nuværende app bør ikke blot eksponeres direkte på internettet.

## 4. Genbrugsvurdering

### 4.1 Bevar

- Streamlit som brugerflade i næste hovedversion.
- SQLite som database for én bruger.
- Den eksterne datamappe og princippet om, at kode og data er adskilt.
- De eksisterende aktør-id'er og tabeller som migrationsgrundlag.
- Aktørprofil, tidslinje, møder, kontakter, opfølgninger, observationer, viden og briefinger.
- `monitor.py`, `connectors.py`, `analysis_engine.py` og `document_utils.py` som separate ansvarsområder.
- Valgfri AI med lokal fallback.
- Git/GitHub som versionshistorik for kode og dokumentation – men aldrig kundedata.

### 4.2 Videreudvikl

- `companies` som generelt aktørregister i brugerfladen. Tabellen kan beholde sit navn i første omgang for at undgå en risikabel migration.
- `followups` som konkrete handlinger, men med mulighed for kobling til en kundeopgave eller et tilbud.
- møder og dokumenter, så et dokument registreres i `uploaded_documents` og kan knyttes til både aktør og opgave;
- kontakter med relationstyrke, seneste kontakt og næste relevante kontakt;
- segmentering med de vigtigste felter fra Excel-arket;
- signaler med forretningsrelevans og kobling til kundeopgaver/ydelser;
- dashboardet med egentlige kundeopgaver og tilbud;
- backup med migrationssikkerhed og restore-test.

### 4.3 Forenkle

- Navigationen: vis daglige arbejdsområder først og administration nederst.
- Statuslister og typer: definér dem ét centralt sted.
- Noter og viden: behold forskellen, men brug én samlet søge-/arbejdsvisning.
- Kilder: vis kun aktive/højprioriterede kilder i daglig drift.
- Signalbehandling: færre signaler, stærkere relevans og klar handling.
- Mødeoprettelse: én mødepost med før-, under- og eftermødenoter i stedet for parallelle poster.

### 4.4 Udfas

- ZIP-patches som normal udviklingsmetode.
- v2.5.3 som aktiv kodebase.
- versionsnoter spredt over mange små tekstfiler; erstat dem gradvist med README og changelog.
- automatisk pakkeinstallation ved hver programstart.
- skjulte/forældede databasefelter uden dokumenteret formål.
- implicitte databaseændringer ved blot at åbne en side.
- direkte interneteksponering af den nuværende Streamlit-app.

## 5. Foreslået arkitektur for version 3.0

### 5.1 Teknologivalg

Streamlit og SQLite er fortsat hensigtsmæssige, fordi:

- der er én bruger;
- datamængden er lille;
- appen er et internt arbejdsredskab;
- hurtig udvikling og enkel drift er vigtigere end flerbruger-skalerbarhed;
- den nuværende kode og data kan genbruges;
- et teknologiskift vil give høj risiko uden tilsvarende forretningsværdi nu.

FastAPI/React eller PostgreSQL bør først overvejes, hvis mindst ét af følgende bliver reelt:

- flere samtidige brugere;
- rettighedsstyring mellem brugere;
- stabil offentlig/cloud-hosting med integrationer;
- større automatiseret databehandling;
- API-adgang fra andre systemer;
- væsentligt højere datamængde eller rapporteringskrav.

### 5.2 Anbefalet kodeopdeling

En pragmatisk struktur kan være:

```text
app.py                         # lille router og fælles layout
pages/
  dashboard.py
  actors.py
  engagements.py              # muligheder, tilbud og kundeopgaver
  tasks.py
  meetings.py
  intelligence.py
  knowledge.py
  settings.py
services/
  briefing_service.py
  document_service.py
  monitoring_service.py
  backup_service.py
repositories/
  actor_repository.py
  engagement_repository.py
  task_repository.py
  meeting_repository.py
  signal_repository.py
db/
  connection.py
  migrations.py
  migrations/
domain/
  statuses.py
  validation.py
tests/
```

Det er ikke nødvendigt at opbygge en tung framework-arkitektur. Formålet er blot at adskille:

- Streamlit-widgets;
- forretningsregler;
- SQL/dataadgang;
- eksterne tjenester;
- migrationer og backup.

### 5.3 Foreslået forretningsmodel

Der bør oprettes én central tabel, foreløbigt kaldet `engagements`, som dækker den kommercielle livscyklus:

- `Mulighed`
- `Tilbud under udarbejdelse`
- `Tilbud sendt`
- `Accepteret`
- `I levering`
- `Afventer kunde`
- `Afsluttet`
- `Tabt`
- `Parkeret`

Vigtige felter:

- aktør;
- titel og kort beskrivelse;
- type: mulighed, tilbud eller kundeopgave;
- fase/status;
- rådgivningsområde;
- sandsynlighed eller prioritet;
- honorarmodel: fast pris, timebasis, klippekort/retainer eller endnu ikke aftalt;
- tilbudt og aftalt honorar, ekskl. moms;
- tilbudsdato, forventet beslutningsdato, startdato og slutdato;
- næste handling;
- fortrolighed;
- oprettet og senest ændret.

Derudover anbefales en enkel `deliverables`-tabel med:

- opgave/engagement;
- titel;
- deadline;
- status;
- leveringsdato;
- note eller filreference.

Eksisterende `followups` bør kunne få et valgfrit `engagement_id`. Det samme kan senere gælde møder, dokumenter og briefinger. Dermed genbruges de nuværende arbejdsflows uden at gøre `followups` til selve kundeopgaven.

### 5.4 Segmenteringsmodel

De mest værdifulde felter fra Excel-arket kan tilføjes til aktøren eller en særskilt profil:

- segment;
- tilladelsesspor;
- strategisk kategori;
- relevansbegrundelse;
- mulig indgang;
- relationstyrke;
- købspotentiale;
- drifts-/myndighedsfølsomhed;
- samlet score;
- fase;
- kernefortælling;
- sandsynlig intern køber.

`Næste skridt` bør ikke dubleres som fritekst, hvis det allerede findes som en åben opfølgning. Ved import bør næste skridt i stedet kunne oprettes som en konkret opgave med kilde `Segmenteringsark`.

### 5.5 Databasesikker udvikling

Før nye felter og tabeller indføres:

1. Opret `schema_migrations` med entydige versionsnumre.
2. Tag SQLite-backup før migration.
3. Kør migrationen i én transaktion.
4. Aktivér foreign keys på alle forbindelser.
5. Kør integritets- og foreign-key-kontrol efter migration.
6. Stop og gendan ved fejl.
7. Test altid mod en kopi af den aktive database først.

## 6. Forslag til nyt dashboard

Dashboardet bør besvare: “Hvad kræver min opmærksomhed nu?”

### 6.1 Øverste handlingslinje

Højst fire nøgletal:

- forfaldne handlinger;
- aktive kundeopgaver;
- tilbud der afventer svar;
- nye højrelevante signaler.

Hvert tal skal kunne åbne den filtrerede liste bag tallet.

### 6.2 Dagens fokus

Den vigtigste blok på siden:

- handlinger i dag og de næste syv dage;
- næste møde med genvej til briefing;
- leverancer med nært forestående deadline;
- tilbud, som bør følges op;
- relationer uden aftalt næste kontakt.

Elementerne sorteres efter deadline og forretningsmæssig prioritet. Dashboardet bør højst vise 8–12 konkrete handlinger ad gangen.

### 6.3 Aktive kunder og opgaver

Vis én kompakt linje pr. aktiv opgave:

- kunde;
- opgavenavn;
- fase;
- næste leverance og deadline;
- næste handling;
- eventuelt aftalt honorar.

### 6.4 Tilbud og muligheder

Vis muligheder og tilbud efter fase:

- kvalificeres;
- tilbud udarbejdes;
- tilbud sendt;
- afventer svar;
- accepteret/tabt.

Der bør være direkte genvej til at registrere næste handling. En simpel liste er bedre end et grafisk kanban-board i første version.

### 6.5 Relationer at følge op på

Vis kontakter, hvor:

- der er en forfalden relationel opfølgning;
- seneste kontakt er gammel;
- personen er knyttet til en aktiv mulighed;
- personen er markeret som vigtig døråbner eller intern køber.

### 6.6 Intelligence

Vis kun:

- nye signaler med høj relevans;
- signaler knyttet til en aktiv kunde, opgave eller højprioriteret mulighed;
- signaler med en konkret foreslået handling.

Alle øvrige signaler hører til i Signalindbakken, ikke på dashboardet.

### 6.7 Hurtige handlinger

Faste genveje til:

- ny opgave;
- nyt møde;
- ny mulighed/tilbud/kundeopgave;
- ny note;
- upload referat.

## 7. Prioriteret udviklingsplan

### Etape 1 – Stabilt fundament og sikker database

**Formål:** Reducere regressionsrisiko, før forretningsmodellen udvides.

**Funktioner:**

- registrér den nuværende database som baseline;
- indfør versionsstyrede migrationer;
- aktivér foreign keys;
- backup før migration og restore-test;
- centrale status-/typelister;
- basale tests for database og vigtigste workflows;
- fjern skrivehandlinger ved ren sidevisning.

**Genbrug:** Hele nuværende database og `db.py` som udgangspunkt.

**Databaseændringer:** `schema_migrations`; eventuelt indekser. Ingen forretningsdata ændres.

**Risici:** Skemadrift mellem kode og aktiv database.

**Test:** Kør mod kopi af aktiv database; sammenlign rækkeantal før/efter; integrity check; foreign-key check; gendannelse fra backup.

### Etape 2 – Modulopdeling uden ændret funktionalitet

**Formål:** Gøre fremtidige ændringer mindre risikable.

**Funktioner:**

- del `app.py` i sider, services og repositories;
- bevar samme navigation og adfærd;
- flyt AI-prompts og dokumentlogik til services;
- opdater README og versionsnavn.

**Genbrug:** Næsten al eksisterende kode flyttes og tilpasses frem for at blive skrevet om.

**Databaseændringer:** Ingen.

**Risici:** Streamlit state og widgetnøgler kan ændre adfærd ved flytning.

**Test:** Smoke-test af alle sider; opret/redigér/slet på en testdatabase; regressionstest af profilnavigation, briefing og mødeupload.

### Etape 3 – Aktør- og segmenteringsgrundlag

**Formål:** Samle markedsliste, prioritering og relationel kontekst i systemet.

**Funktioner:**

- nye segmenteringsfelter;
- importforhåndsvisning fra Excel;
- navnenormalisering og dubletforslag;
- manuel godkendelse pr. match;
- opret næste skridt som opgave;
- vis strategisk kategori og fase på aktørprofilen.

**Genbrug:** Eksisterende aktører, prioritet, kontakter og opfølgninger.

**Databaseændringer:** Nye aktørfelter eller en enkel `actor_strategy`-tabel.

**Risici:** Dubletter, modstridende oplysninger og to samtidige “sandheder” i Excel og database.

**Test:** Import mod databasekopi; 17 eksakte matches plus navnevarianten ALK; ingen automatisk overskrivning; tydelig rapport over nye/ændrede poster.

### Etape 4 – Muligheder, tilbud og kundeopgaver

**Formål:** Understøtte den faktiske rådgivningsforretning.

**Funktioner:**

- opret og redigér engagement;
- enkel livscyklus fra mulighed til afsluttet opgave;
- honorar og vigtige datoer;
- leverancer og deadlines;
- kobling til aktør, kontakter, møder og opfølgninger;
- historik over statusændringer i let form.

**Genbrug:** `followups`, kontakter, møder, dokumenter og aktørprofiler.

**Databaseændringer:** `engagements`, `deliverables`, valgfrit `engagement_id` på relevante tabeller.

**Risici:** For mange statusser og overlap med opfølgningsmodulet.

**Test:** Gennemfør tre scenarier: tabt tilbud, accepteret fastprisopgave og løbende rådgivningsforløb. Kontrollér deadlines, afslutning og historik.

### Etape 5 – Dashboard 3.0

**Formål:** Gøre startsiden til det daglige arbejdsbord.

**Funktioner:**

- dagens fokus;
- aktive kundeopgaver;
- tilbud/muligheder;
- kommende møder og leverancer;
- relationelle opfølgninger;
- få, målrettede signaler;
- hurtige handlinger og direkte navigation.

**Genbrug:** Nuværende dashboard, deadlinegrupper, mødegenveje og signaltælling.

**Databaseændringer:** Ingen ud over etape 4; eventuelt indekser til dashboardforespørgsler.

**Risici:** For meget information på én side og langsomme gentagne SQL-kald.

**Test:** Brug dashboardet dagligt i 1–2 uger; registrér hvilke elementer der faktisk udløser handling; test normal vinduesbredde og iPad-bredde.

### Etape 6 – Målrettet Intelligence Monitor

**Formål:** Reducere støj og koble overvågningen til reel forretningsværdi.

**Funktioner:**

- overvågningsniveau pr. aktør;
- relevans for kundeopgave, tilbud eller rådgivningsområde;
- bedre alias- og nøgleordsmatch;
- læring fra irrelevante signaler;
- forklaring på, hvorfor et signal er relevant;
- enkel dublet-/hændelsessamling.

**Genbrug:** Kilder, triggerregler, signalindbakke, `monitor.py` og regelbaseret fallback.

**Databaseændringer:** Relevanskoblinger og eventuelt et lille feedback-/event-clusterlag.

**Risici:** Overautomatisering, falske positiver og kildebegrænsninger.

**Test:** Mål andelen af gemte/relevante signaler mod de nuværende 25 %. Ingen ny kilde tilføjes uden en tydelig nytte-test.

### Etape 7 – AI, fortrolighed og valgfri fjernadgang

**Formål:** Bevare AI-værdi uden at gøre systemet afhængigt af API-kald eller skabe unødig risiko.

**Funktioner:**

- synlig forhåndsvisning af data, der sendes til AI;
- valg om at udelade fortrolige felter;
- AI-handlinger pr. møde, opgave eller signal;
- ingen automatisk afsendelse;
- beslutningspunkt om sikker hosting til iPad uden tændt PC.

**Genbrug:** Eksisterende briefing- og opfølgningsprompts samt lokal fallback.

**Databaseændringer:** Eventuelt log over AI-handlingens tidspunkt og datakategori – ikke API-nøgler eller fulde prompts med følsomme data.

**Risici:** Fortrolighed, persondata, leverandørafhængighed og driftsomkostning.

**Test:** Test uden API-nøgle, med API-fejl og med fravalg af fortrolige data. Cloudspor kræver særskilt sikkerheds- og backupgodkendelse.

## 8. Afklaringsspørgsmål før implementering

Kun følgende beslutninger vurderes nødvendige før udviklingen starter:

1. **Forretningsforløb:** Er denne standardproces dækkende: `Mulighed → Kvalificering → Tilbud udarbejdes → Tilbud sendt → Accepteret/I levering → Afsluttet`, med `Tabt` og `Parkeret` som sideudgange?
   - Anbefalet udgangspunkt: Ja, og hold listen fast i første version.

2. **Honorarmodel:** Skal systemet kunne registrere fast pris, timepris og retainer/klippekort, eller er ét samlet beløb nok i første version?
   - Anbefalet udgangspunkt: Honorarmodel + tilbudt/aftalt beløb ekskl. moms; ingen fakturering eller Billy-integration.

3. **Aktiv kunde:** Hvornår skal en aktør vises som kunde – ved mundtlig accept, underskrevet tilbud eller første fakturerbare aktivitet?
   - Anbefalet udgangspunkt: Ved accepteret tilbud eller eksplicit registrering som aktiv kunde.

4. **Segmenteringsark:** Skal arket importeres én gang, hvorefter Dashboard 3.0 bliver primær kilde, eller skal Excel fortsat være en parallel master?
   - Anbefalet udgangspunkt: Kontrolleret engangsimport; derefter er Dashboard 3.0 primær kilde.

5. **AI og fortrolighed:** Må mødenoter og kundedata som udgangspunkt sendes til OpenAI ved en manuel AI-handling, eller skal poster markeret `Fortrolig` altid udelukkes?
   - Anbefalet udgangspunkt: Fortrolige poster udelukkes som standard og kræver aktivt tilvalg.

6. **iPad uden PC:** Er sikker fjernadgang et krav til første 3.0-version, eller kan det være en senere særskilt etape efter den lokale løsning er stabil?
   - Anbefalet udgangspunkt: Senere etape. Lokal stabilitet og forretningsmodul først.

7. **Backup:** Skal backup kun beskytte mod programfejl, eller også mod tab/tyveri af PC'en?
   - Anbefalet udgangspunkt: Begge dele; behold lokal backup og tilføj senere krypteret ekstern kopi af database og dokumenter.

## 9. Foreslået godkendelse af fase 1

Hvis denne plan godkendes, bør næste arbejde begrænses til **Etape 1 – Stabilt fundament og sikker database**.

Det betyder konkret, at der endnu ikke bygges et nyt dashboard eller et tilbudsmodul. Først etableres en sikker baseline, tests, migrationsstyring og en dokumenteret gendannelsesvej. Derefter kan kundeopgaver og tilbud tilføjes uden at gentage de tidligere hotfix-forløb.

## 10. Dokumenterede usikkerheder

- Den angivne skrivebordskopi af `monitor.db` fandtes ikke på den oplyste sti. Analysen bruger derfor den aktive database i `FrankAdvisoryMonitorData`.
- Segmenteringsarket har 489 formaterede rækker, men kun 18 reelle masterlisteposter. En import må ikke tolke formaterede tomme rækker som data.
- Den aktive database indeholder ældre felter/tabeller, som ikke er fuldt repræsenteret i den aktuelle kildekode. Deres fremtidige anvendelse skal afklares under skemabaseline i etape 1.
- Denne fase har ikke testet eksterne websites, feeds eller OpenAI-kald, fordi eksterne kald udtrykkeligt var fravalgt.
- Der er ikke foretaget en egentlig restore af en backup i fase 1, fordi det ville kræve oprettelse og åbning af en særskilt testkopi. Det bør være første praktiske test i etape 1.
