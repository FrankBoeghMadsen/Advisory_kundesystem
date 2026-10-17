# Etape 3 - implementering af forretningsmodul

## Resultat

Etape 3 tilføjer et afgrænset forretningsmodul til den eksisterende Streamlit-app. Eksisterende navigation og funktioner er bevaret. Modulet håndterer konkrete forretningsforløb, tilbud, kundeopgaver, leverancer og deadlines uden at gøre almindelige relationer til salgsmuligheder.

Implementeringen er udført og testet uden at åbne den aktive database via SQLite eller ændre den.

## Databaseisolering

`runtime_config.py` indfører tre eksplicitte tilstande: `production`, `development` og `test`.

- `Start Monitor.bat` vælger `production` og `%USERPROFILE%\FrankAdvisoryMonitorData`.
- `Start Monitor Development.bat` vælger `development` og den Git-ignorerede mappe `.dev-data`.
- Direkte start uden tilstand stopper før databaseadgang.
- Produktion kan ikke omdirigeres til en anden datamappe.
- Udvikling og test afvises, hvis en skriveforbindelse peger på produktionsmappen eller en undermappe i den.
- Tilstanden og den anvendte datamappe vises i sidepanelet. Udvikling vises med en tydelig advarsel.
- Testene bruger udelukkende midlertidige databaser under `.test-tmp`.

Backup-startfilen angiver ligeledes produktionstilstand eksplicit. Den tidligere lokale databasekopiering kan kun forekomme i produktionstilstand.

## Migration 004

Migration `004_business_module` er additiv og opretter:

- `commercial_tracks`: forretningsforløb under en aktør.
- `proposals`: tilbud og versioner under et forretningsforløb.
- `engagements`: direkte eller tilbudsbaserede kundeopgaver.
- `deliverables`: leverancer og deadlines under en kundeopgave.
- `meeting_tracks`: mange-til-mange-kobling mellem møder og forretningsforløb.
- Valgfrie koblinger fra `followups` til forretningsforløb og leverancer.

Tilbud har struktureret honorarmodel, tilbudt honorar ekskl. moms, honorarnote og dokumentreference. Kundeopgaver har aftalt honorarmodel, aftalt honorar ekskl. moms og honorarnote. Der er ikke tilføjet fakturering, bogføring eller betalingsstyring.

Ved første produktionsstart med migration 004 vil den eksisterende migrationsmekanisme oprette og verificere en `pre_migration`-backup, før den aktive database migreres. Dette er bevidst ikke udført som led i udvikling og test.

## Brugerflade

Den nye hovedvisning **Forretning** har fem arbejdsområder:

- **Pipeline:** oprettelse og redigering af forretningsforløb samt kobling til primær kontakt, møder og opfølgninger.
- **Tilbud:** versionsstyrede tilbud, status, honorar og valgfri dokumentreference.
- **Kundeopgaver:** direkte oprettelse eller eksplicit oprettelse fra et accepteret tilbud med forudfyldte oplysninger.
- **Deadlines:** leverancer, status, prioritet, deadline og koblede opfølgninger.
- **Afsluttet:** afsluttede kundeopgaver og lukkede forretningsforløb.

Aktørprofilen har fået sektionen **Forretning**. Dashboardet viser antal åbne forløb, tilbud der afventer, aktive kundeopgaver og åbne leverancer. Opgaveoversigten viser en eventuel kobling til forretningsforløb og leverance.

## Dobbeltregistrering og automatisering

- Aktører, kontakter, møder, referater og opfølgninger genbruges via relationer.
- Ét møde kan knyttes til flere forretningsforløb.
- Koblinger på tværs af aktører afvises.
- Alternative eller reviderede tilbud bruger samme forretningsforløb og forskellige versionsnumre.
- Et tilbud opretter kun en kundeopgave efter aktiv indsendelse af konverteringsformularen.
- En kundeopgave kan oprettes direkte uden et tilbud.
- Fremtidigt samarbejde registreres som note og bliver ikke automatisk til et nyt forretningsforløb.

## Gennemførte tests

Den samlede automatiserede testsuite omfatter 18 tests:

- Alle navigationsvisninger har en renderer og kan indlæses uden undtagelser.
- Forretningsvisningen kan indlæses med syntetiske kommercielle data.
- En frisk database anvender migration 001-004 og består integritetskontrol.
- En eksisterende database sikkerhedskopieres før migration og bevarer data.
- Backup kan gendannes og verificeres isoleret.
- Udvikling/test kan ikke anvende produktionsmappen eller en database i den til skrivning.
- Produktion kan ikke omdirigeres til en vilkårlig datamappe.
- Begge Windows-startfiler binder kun til `127.0.0.1` og vælger korrekt datatilstand.
- AI-funktioner kræver fortsat aktivt samtykke til ekstern overførsel.
- Nomeco-scenariet er testet som direkte, historisk og afsluttet kundeopgave uden tilbud.
- Glostrup Apotek-scenariet er testet med flere forløb, flere tilbud, honorarforskel og eksplicit oprettelse af kundeopgave.
- TMJ-scenariet er testet med møde, men uden automatisk forretningsforløb.
- Ét møde kan knyttes til flere forløb.
- Eksisterende opfølgninger kan kobles til forløb og leverancer uden kopiering.
- Koblinger til møder eller opfølgninger hos en anden aktør afvises.

Derudover er siden kontrolleret visuelt med syntetiske data på desktop- og mobilbredde. Navigation, faner, filtre og formularer blev vist uden overlap, vandret overløb eller browserfejl.

## Aktiv database og testdata

Den aktive database er ikke åbnet via SQLite, migreret eller ændret under etape 3. Alle databaseoperationer er kørt mod midlertidige eller særskilte testdatabaser. De illustrative Nomeco-, Glostrup Apotek- og TMJ-poster findes kun i testkørslerne.

Som afsluttende, skrivebeskyttet kontrol blev filens metadata og SHA-256 sammenlignet med kontrollen efter etape 2:

- Senest ændret: `17-10-2026 02:08:46`.
- SHA-256: `CF29B63A4855F9B337FF52367E7F7B4B64BC5DA506460EA575106F8C6E56E524`.

Begge værdier er uændrede.

## Rollback

- Koden kan føres tilbage til commit før etape 3.
- Migration 004 er additiv, så den tidligere programversion ignorerer de nye tabeller og kolonner.
- Hvis en helt identisk tidligere database ønskes efter første produktionsstart, stoppes programmet, og den automatisk oprettede `monitor_pre_migration_*.db` kan gendannes manuelt.

## Udestående og bevidste afgrænsninger

- Den aktive database får først migration 004, når den godkendte produktionsversion startes.
- Tilbudsdokumenter uploades ikke; der gemmes kun en valgfri reference.
- Der er ingen fakturering, bogføring, betalingsovervågning eller økonomirapportering.
- Der er ingen automatisk oprettelse af forretningsforløb, tilbud, kundeopgaver eller nye samarbejder.
- Hosting og fjernadgang er ikke ændret.

Etape 3 stopper her og afventer ejerens godkendelse.
