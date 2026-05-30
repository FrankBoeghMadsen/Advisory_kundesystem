# Frank Advisory Intelligence Monitor v2.4

En første fungerende MVP som lokal Streamlit-webapp til passiv overvågning af danske life science-virksomheder.

## Hvad den kan
- Oprette/redigere virksomheder, kilder, triggerregler, kontaktpersoner og noter
- Køre manuel overvågning via konfigurerbare kilder
- Indsamle fund fra RSS/nyhedsfeeds og simple web-kilder
- Score fund som Lav/Middel/Høj/Kritisk
- Markere myndighedsreaktioner og andre relevante signaler
- Vise dashboard, signalindbakke, virksomhedsprofiler og noter
- Eksportere signaler til CSV
- Bruge OpenAI til opsummering/scoring, hvis `OPENAI_API_KEY` sættes; ellers bruges regelbaseret scoring

## Kom hurtigt i gang

```bash
cd frank_advisory_monitor_v2_4
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Første gang appen startes, oprettes en lokal SQLite-database med virksomhederne fra masterlisten.

## Valgfri AI-analyse

Opret en `.env`-fil:

```bash
OPENAI_API_KEY=din_api_noegle
OPENAI_MODEL=gpt-4.1-mini
```

Uden nøgle virker appen stadig med regelbaseret scoring.

## Bemærk
Denne MVP bruger kun konfigurerbare offentlige feeds/web-kilder. LinkedIn er ikke automatiseret.

## Begrebet "virksomhed"

I den nuværende datamodel hedder den centrale aktør stadig `virksomhed`. I praksis kan den også bruges til brancheforeninger, vigtige relationer, rådgivere, kaffemødekontakter eller andre aktører, som Frank Advisory ønsker at følge over tid.

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
