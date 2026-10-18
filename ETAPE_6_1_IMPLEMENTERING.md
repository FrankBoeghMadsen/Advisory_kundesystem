# Etape 6.1 - valgfri projektkerne

## Afgrænsning og ændringer

Implementeret på `codex/dashboard-3-foundation` med udgangspunkt i `0c980d0` og det godkendte kravgrundlag fra etape 6.0.

- Forretning har en ny valgfri visning: Forløb / Projekter. Eksisterende forløb, tilbud, enkeltkundeopgaver, leverancer og dashboardlinks bevares. Direkte åbning fra projektet vælger det eksisterende forløb uden omveje.
- Projekt kan oprettes med titel, formål og status, helt uden deltagere, forløb, tilbud eller kundeopgave. Intet økonomisk hovedanker kræves eller implementeres i 6.1.
- Deltagervirksomhed kan have flere samtidige roller: Koordinator, Aftalepart, Betaler, Deltager og Begunstiget. Roller kan også stå tomme. De er beskrivende metadata og opretter ingen aftale, betalingspligt eller økonomiske poster.
- Faglige spor kan være fælles eller knyttet til en projektdeltager. Spor har titel og enkel status; de opretter ikke salgsmuligheder, tilbud, kundeopgaver eller leverancer.
- Eksisterende forløb kan tilknyttes eksplicit, åbnes og frakobles. Forløbets virksomhed skal være projektdeltager. Frakobling sletter ikke forløbet eller dets historik.
- Projektoversigten viser alene projektdata, deltagere/roller, spor og eksplicit tilknyttede forløb. Ingen nye projektaktiviteter, mødekontekster, initiativtyper, personidentiteter, afhængigheder, dokumentregister eller økonomifunktioner fra 6.2–6.6.

Koden er afgrænset til `services/project_service.py`, `views/projects.py`, en lille visningsvælger i Forretning, en navigationsanmodning til eksisterende forløb og migration 8. Den gamle forretningsstruktur er ikke omskrevet.

## Datamodel og migration 8

Fire nye tabeller:

| Tabel | Indhold |
| --- | --- |
| `projects` | Titel, formål, status og oprettelses-/ændringstidspunkt. Ingen virksomheds-, forløbs- eller opgavereference er påkrævet. |
| `project_companies` | Unik projekt/virksomhed-relation med fem uafhængige 0/1-rollefelter. Virksomheden forekommer kun én gang pr. projekt, også ved flere roller. |
| `project_workstreams` | Projekt, titel, status og valgfri deltagervirksomhed. NULL virksomhed betyder fælles spor. Flere spor pr. virksomhed er mulige. |
| `project_tracks` | Eksplicit kobling til eksisterende kommercielt forløb. I 6.1 kan et forløb være knyttet til højst ét projekt. |

Der tilføjes ikke kolonner til eksisterende forretningsobjekter, og eksisterende feltværdier eller aftalehistorik omskrives ikke. Koblingstabel frem for et projektfelt på forløbet holder den gamle struktur isoleret. Ingen automatisk konvertering eller dataseeding af projekter.

Der er PK/UNIQUE, status- og rolle-CHECK, deklarerede FK samt målrettede relationstriggere. De nye skrivninger foregår i transaktioner med `BEGIN IMMEDIATE`, med kontrol af eksisterende ID'er og projektmedlemskab. Deltager kan ikke fjernes, mens vedkommendes virksomhed har spor eller tilknyttede forløb. Sletning/flytning af refererede virksomheder, forløb og projektnøgler beskyttes af snævre triggere, også via de ældre forbindelser.

## Særskilt teknisk risiko: globale foreign keys

Den eksisterende `db.connect()` aktiverer fortsat ikke `PRAGMA foreign_keys=ON`. Det er **ikke ændret globalt eller lokalt i projektservicen**. Den isolerede test bekræfter uændret indstilling 0. Deklarerede FK alene er derfor fortsat ikke en garanti for alle gamle relationer. Denne risiko gælder især ældre slette-/flytteveje og kræver en selvstændigt godkendt analyse før eventuel global aktivering.

For de nye projektrelationer kontrollerer service og målrettede triggere gyldige forældre, medlemskab og relevante slette-/nøgleændringer. Tests fremprovokerer ugyldige relationer direkte gennem en almindelig forbindelse med FK slået fra. `foreign_key_check` anvendes desuden som efterkontrol. Det er en afgrænset sikring, ikke en påstand om, at SQLite-filen er beskyttet mod vilkårlig manuel ombygning af skema eller deaktivering af triggere.

## Udviklingsmigration, backup og tilbageførsel

- Test og browserkontrol bruger nye isolerede syntetiske databaser. Der er ikke importeret faktiske kundeoplysninger eller anvendt aktive kunde-/driftsdata. Nye scenarier bruger TEST Alfa og TEST Beta. Eksisterende regressionstests genbruger deres tidligere syntetiske fixtures.
- En kørende udviklingsproces stopper før migration 8, medmindre den er startet med den nye eksplicitte markering. Genstart via `Start Monitor Development.bat` sætter markeringen og bruger fortsat `.dev-data`. Ingen eksisterende udviklingsdatabase er startet eller migreret som led i denne aflevering.
- Ved din senere udviklingsgenstart tager den eksisterende migrationsmekanisme først en verificeret SQLite-backup, anvender migrationen og kontrollerer integritet/FK. Nye databaser behøver ingen før-backup, da der ikke er tidligere data at gendanne.
- Test af migration fra version 7 bevarer gamle virksomhed-, kontakt-, forløbs-, tilbuds-, opgave-, leverance-, møde- og opfølgningsrækker, herunder afslutningsnote/dato. Backup har fortsat skemaversion 7 og kan gendannes til en separat mappe med integritet OK.
- Tilbageførsel: stop skrivende udviklingssessioner, bevar den nye database som separat kopi, gendan før-backup til ny mappe og brug den tilsvarende tidligere kodeversion. Kontroller før stiskift; overskriv ikke en åben database. Nye projektregistreringer efter migrationen indgår ikke i før-backup og skal bevares særskilt, hvis de ønskes genanvendt.
- Driftsspærren og den almindelige driftsstartfil er uændrede. Ingen driftsdatabase er oprettet, migreret eller ændret. Driftsdatabasens SHA256 før/efter er `B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.

## Automatiske tests

Kommando: `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`.

**47 tests bestået: 41 tidligere tests og 6 nye projekt-tests.**

De nye tests dækker:

1. Projekt uden aftale/forløb, flere roller, tom rolleliste, fælles og virksomhedsspecifikt spor samt redigering; kommercielle rækker forbliver uændrede.
2. Validering af titel/status, ugyldige ID'er, manglende medlemskab, forkert projekt, én projekttilknytning pr. forløb og sikker frakobling/fjernelse.
3. Direkte ugyldige SQL-skrivninger afvises også med foreign keys slået fra, herunder sletning/flytning af refererede forældre og forkert sporstatus.
4. Migration fra version 7, backup før migration, bevarede historiske rækker, tomme nye projekttabeller, gendannelseskontrol og ingen FK-fejl.
5. Automatisk udviklingsgenindlæsning uden ny migrationsmarkering stopper før databaseskrivning.
6. Interaktiv Streamlit AppTest: tom oprettelse afvises, projekt/deltager med flere roller/spor oprettes, eksisterende forløb kobles og åbnes; gentagen projektvisning ændrer ikke databasen (sammenligning af hele SQL-dumpet).

De tidligere tests dækker bl.a. enkeltkundeopgaver, honorarbeskyttelse, aftaleændringer, dashboardnavigation, møder, opfølgningers historik og driftssikkerhed. Der er ikke indført nye obligatoriske felter på disse arbejdsgange.

## Browserkontrol

Edge, separat testserver på 127.0.0.1:8517 med nye syntetiske TEST Alfa/TEST Beta-data: projektoversigt med flere roller, fælles og virksomhedsspecifikt spor; direkte åbning af eksisterende forløb; skift tilbage til Projekter; oprettelse af TEST Projekt uden aftale med tom deltager-/forløbs-/sporliste. Ingen aftale eller økonomisk anker var nødvendigt. Visuel kontrol ved desktopbredde 1231 px gav intet vandret side-overløb. Ingen observerede applikationsfejl; en separat adblock-udvidelse rapporterede en konsolfejl. Mobilvisning er ikke gentestet i 6.1.

Den isolerede testserver stoppes efter kontrol. Brugerens eksisterende sessioner og startkonfiguration til drift er ikke berørt.

## Manuel prøvevejledning

1. Stop den gamle udviklingssession og start `Start Monitor Development.bat`. Kontroller UDVIKLING og `.dev-data`; brug ikke driftsstarten. Første genstart tager backup og migrerer udviklingsdatabasen.
2. Vælg Forretning → Projekter → Opret projekt. Opret et TEST-projekt alene med titel. Det skal eksistere uden aftale, forløb eller kundeopgave.
3. Under Tilføj / redigér deltager: vælg en eksisterende testvirksomhed, vælg fx Koordinator og Betaler samtidigt, og Gem deltager. Kontroller én virksomhedsrække med begge roller. Der skal ikke oprettes økonomiske poster.
4. Tilføj en anden testvirksomhed. Opret et fælles spor og et virksomhedsspor; rediger titel/status. Sporene skal være uafhængige af kommercielle forløb.
5. Tilknyt et eksisterende TEST-forløb hos en deltager. Åbn det, og kontroller, at den tidligere Pipeline/Tilbud/Kundeopgaver-navigation fungerer. Skift tilbage til Projekter.
6. Frakobl forløbet. Kontroller, at det stadig findes i Forløb. Forsøg at fjerne en deltager med eget spor: systemet skal afvise det, indtil sporet er flyttet til fælles eller slettet efter bekræftelse.
7. Skift til Forløb og opret/rediger en almindelig testkundeopgave som hidtil. Intet projektvalg må være nødvendigt.

## Kendte afgrænsninger

- Ingen hovedanker-, honorar-, betalings- eller fakturafelter. Roller etablerer ingen betalingspligt eller solidarisk hæftelse. Den senere ønskede fælles projektøkonomi med flere selvstændige forpligtelser er alene fremtidigt kravgrundlag.
- Spor er enkle registreringer med selvstændig status. De er ikke koblet til møder, aktiviteter, deadlines eller leverancer endnu; det hører til en eventuel godkendt 6.2.
- Projekt kan afsluttes/annulleres via status. Der er ingen permanent projektsletning i brugerfladen. Arbejdsspor kan slettes efter bekræftelse; deltager- og forløbskoblinger kan fjernes uden sletning af stamdata.
- Ét forløb kan højst tilhøre ét projekt. En virksomhed kan deltage i flere projekter og have flere roller/spor. Et projekt kan også stå helt uden virksomheder.
- Roller og spor har ikke en revisionslog. Eksisterende aftalehistorik og opfølgningshistorik er ikke ændret.
- AppTest har en widget-serialiseringsbegrænsning ved genbrug af samme testobjekt efter visse dynamiske sideskift; genåbnet projektvisning er derfor også testet i en frisk session. Reel browsernavigation kontrolleres særskilt.

Præciseringen om bestyrelsens godkendelse af det oprindelige Megros-tilbud, meddelt den 3. september 2026, er føjet til etape 6.0-rapporten alene som kravgrundlag. Ingen faktiske kundeoplysninger er oprettet i databasen.

Stop efter 6.1. Næste etape og enhver driftsoverførsel kræver særskilt godkendelse.
