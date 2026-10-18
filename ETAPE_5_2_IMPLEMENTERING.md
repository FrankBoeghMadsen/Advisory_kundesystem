# Etape 5.2 - afsluttende forbedringer

Dato: 18. oktober 2026. Udgangspunkt: `648aef5`, gren `codex/dashboard-3-foundation`.

## Undersøgelse og ændringer

Afslutning fandtes allerede: status Lukket fjernede opfølgningen fra dashboardets åbne aktiviteter uden at slette posten. Virksomhedsprofilens Opfølgning viste også lukkede poster. Det er bevaret. Der manglede særskilt afslutningsdato og resultat.

- Migration 7 tilføjer kun `followups.completed_at` og `completion_result` samt to SQLite-triggere. Overgang til Lukket registrerer UTC-tidspunkt; visningen bruger dansk dato og tidszone. En noteændring på en allerede lukket post ændrer ikke afslutningsdatoen. Genåbning bevarer seneste afslutning og resultat; en ny afslutning registrerer et nyt tidspunkt.
- Resultat / afslutningsnote kan gemmes sammen med Afslut opfølgning eller ved almindelig redigering, både i opfølgningsoversigten og virksomhedsprofilen. Oprindelige felter, ID og koblinger bevares. Sletning er fortsat særskilt og kræver bekræftelse.
- Forløbet viser nu Afsluttede opfølgninger med resultat og direkte Åbn. Resultatet genbruges også i den eksisterende virksomhedstidslinje, uden nye hændelsesposter. Åbne opfølgninger har en direkte Redigér opfølgning-knap i forløbet.
- Dashboardet filtrerer fortsat Lukket og Arkiveret fra. Aktiviteter sorteres efter dato og derefter prioritet. Dashboardets struktur og eksisterende dubletgruppering er uændret.
- Statusfiltrenes chips har lys baggrund, mørk tekst og diskret kant, kun under Forretning. Fravalg og aktive forretningsområder fungerer som før.

## Koblinger uden dobbeltregistrering

Datamodellen havde allerede `company_id`, `commercial_track_id` og `deliverable_id`. Pipeline indeholdt redigering af eksisterende opfølgningskoblinger, og leverancer kunne allerede tilknytte opfølgninger. En virksomhedstilknytning gav ikke automatisk en forløbstilknytning; derfor kunne en selvstændig opfølgning være synlig på dashboardet uden at stå i forløbet.

Oprettelse og redigering i Opfølgninger har nu et valgfrit Forretningsforløb-felt for den valgte virksomhed. Der oprettes ikke et nyt forløb, og ingen relation bliver automatisk til en salgsmulighed. En opfølgning kan fortsat stå uden både virksomhed og forløb. Leverancekobling sker fortsat i den eksisterende leverancevisning; den giver indirekte kobling til kundeopgaven. Skift/fjernelse af forløb fjerner en eventuel leverancekobling fra det gamle forløb, så sammenhængen ikke bliver forkert. Uændret forløb bevarer leverancekoblingen.

## Migration og sikkerhed

Migrationen er additiv og afprøvet på nye, isolerede testdatabaser. Eksisterende lukkede poster får ikke en opdigtet afslutningsdato. Før migration af en eksisterende udviklingsdatabase anvendes den eksisterende SQLite-backup og integritetskontrol.

En allerede kørende udviklingsproces må ikke udføre migration 7 ved genindlæsning. Den stopper med besked om genstart via `Start Monitor Development.bat`. Denne startfil sætter den eksplicitte migrationsmarkering og bruger fortsat `.dev-data`, ikke drift. Der er ikke startet eller migreret nogen eksisterende udviklingsdatabase som led i testarbejdet. Ved din senere genstart migreres kun udviklingsdatabasen med backup først.

Driftsspærren er bevaret. Ingen driftsdatabase er oprettet, åbnet til skrivning, migreret, ryddet op eller importeret. Ingen nye afhængigheder, scraping eller eksterne tjenestekald. `main` er uændret. Syntetisk browsertest bruger en ny database under `.stage5-test-data/stage52-browser` på separat lokal port 8517.

Driftsdatabasens SHA256 før/efter:
`B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.

## Automatiske tests

Kommando: `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`.

41 tests består. Fem nye tests dækker:

1. Migration fra version 6: alle gamle feltværdier bevares, gamle lukkede poster får ikke dato, backup har tidligere skema, gendannelse og integritet er OK.
2. Afslutning, bevaret resultat/virksomhed/forløb/leverance, uændret dato ved noterettelse og bevaret resultat ved genåbning. Forkert virksomheds forløb afvises.
3. Genindlæsning i udvikling stopper før oprettelse/migration uden eksplicit genstart.
4. Interaktiv AppTest: opret med virksomhed og forløb, afslut med resultat, kontrollér dashboard, genfind under virksomheden og forløbet, åbn lukket post direkte. Ingen foreign-key-fejl.
5. Åbne opfølgninger sorteres efter dato/prioritet, mens lukkede ikke indgår i aktiviteter eller tællere.

De øvrige 36 regressionstests omfatter navigation, møder, opfølgninger, tilbud, honorarbeskyttelse, aftaleændringer, leverancer, backup/gendannelse og sikkerhedsspærrer. Testresultatet er målrettet testdækning, ikke en garanti for alle gamle data eller alle mulige brugerforløb.

## Browserkontrol

Gennemført i Edge på separat testserver med syntetiske data: Åbn fra dashboard, udfyld resultat, Afslut opfølgning, verificér dansk afslutningstidspunkt og bevaret note, og vend tilbage til dashboard. Åbne opfølgninger faldt fra 1 til 0, og aktiviteten forsvandt. Under Forretning kunne den lukkede post genfindes i Afsluttede opfølgninger med samme resultat.

Statusfiltrene er visuelt kontrolleret og har beregnet lys baggrund `rgb(233,239,236)` og mørk tekst `rgb(36,59,53)`. Tastaturfravalg og genvalg er afprøvet. Markeringen af aktivt forretningsområde og tællerne er bevaret. Ingen vandret side-overløb ved den kontrollerede desktopbredde 1231 px. Ingen observerede applikationsfejl i konsollen; browserudvidelsen rapporterede en separat adblock-fejl, som ikke stammede fra appen. Mobilvisning er ikke gentestet i denne etape.

## Praktisk prøvevejledning

1. Stop din gamle udviklingssession, og start `Start Monitor Development.bat`. Kontroller at der står UDVIKLING og `.dev-data`, aldrig drift. Den nødvendige migration tager automatisk backup først.
2. Under Møder og opfølgninger: vælg Opfølgninger, opret en testopfølgning hos en testkunde, vælg eventuelt Forretningsforløb, og gem.
3. Åbn fra dashboardet. Skriv et resultat, fx TEST: Dokumentation modtaget den 22. oktober, og vælg Afslut opfølgning. Kontroller afslutningstidspunktet.
4. Gå til dashboardet igen: posten skal være væk fra udeståender, og Åbne opfølgninger skal være faldet med én.
5. Find posten i virksomhedens Opfølgning og i forløbets Afsluttede opfølgninger. Resultatet skal stadig være der. Brug Åbn for at rette noten; datoen skal ikke flytte sig ved almindelig noterettelse.
6. En opfølgning uden forløb findes stadig hos virksomheden. Tilknyt den via opfølgningens redigering eller den eksisterende koblingsfunktion under Pipeline. Ingen ny opfølgning skal oprettes.
7. Kontroller de lyse Status på forløb-filtre: fravælg og genvælg en status. Aktivt forretningsområde og tællere skal fortsat være tydeligt markeret.

## Begrænsninger

- Gamle lukkede poster kan mangle afslutningsdato. Resultatfeltet kan bruges til kendt historisk dato; der er ikke gennemført automatisk udfyldning.
- Der gemmes seneste afslutningsdato og den redigerbare resultatnote, ikke en fuld revisionslog over hver genåbning og hver noterettelse. Arkivering er ikke det samme som en dokumenteret afslutning.
- En opfølgning har fortsat højst ét forløb og én leverance. Der er ikke tilføjet direkte kundeopgavekobling; leverancen giver den eksisterende indirekte relation.
- Tidslinjens opfølgning beholder sin eksisterende datoplacering. Afslutning opretter ikke en ekstra tidslinjehændelse.
- Valg af virksomhed/forløb ved oprettelse ligger uden for gemmeformularen, så forløbslisten opdateres ved virksomhedsvalg. Selve opfølgningen oprettes kun ved Gem opfølgning.

Planen for ren drift og de første kunder findes i [ETAPE_5_2_DRIFTSPLAN.md](ETAPE_5_2_DRIFTSPLAN.md). Den er alene analyse. Arbejdet stopper efter etape 5.2; drift kræver særskilt godkendelse.
