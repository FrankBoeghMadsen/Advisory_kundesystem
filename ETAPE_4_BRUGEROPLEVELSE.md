# Etape 4: brugeroplevelse, honorarer og aftalegrundlag

Aflevering: 18. oktober 2026. Gren: `codex/dashboard-3-foundation`.

## Implementerede ændringer

### Honorarregistrering

Fejlen i etape 3 skyldtes en afkrydsning inde i en Streamlit-formular. En ændring i afkrydsningen blev først sendt til serveren ved indsendelse, så beløbsfeltet forblev deaktiveret.

Afkrydsningerne er fjernet. Honorarmodellen skifter nu felterne med det samme. Beløb og timer indtastes i valgfrie tekstfelter med dansk talformat og valideres før lagring. Der er ingen plus/minus-knapper.

| Model | Felter |
| --- | --- |
| Fast pris | Samlet honorar ekskl. moms |
| Timepris | Timepris ekskl. moms, valgfrit aftalt timeloft og honorarloft |
| Klippekort / retainer | Samlet honorar ekskl. moms og valgfrie inkluderede timer |
| Endnu ikke aftalt | Ingen obligatoriske beløbsfelter; allerede registrerede beløb kan fortsat læses og rettes |

Alle modeller har en valgfri honorarnote. Der er ingen obligatoriske timeestimater.

- Et tomt beløb gemmes som SQL `NULL` og vises som **Honorar ikke registreret**.
- Et indtastet `0` gemmes som nul og vises som **0,00 kr.**
- Eksempelvis `12.500,50` gemmes som beløbet 12500,50.
- Negative tal, forkert gruppering og mere end to decimaler afvises med en dansk fejlmeddelelse.
- Timepris vises med enheden kr./time, så den ikke fremstår som et samlet honorar.

Eksisterende nulbeløb er bevaret. Det kan ikke afgøres automatisk, om et tidligere nul var tilsigtet eller skyldtes fejlen i den gamle formular. Disse registreringer skal vurderes enkeltvis af ejeren.

### Accepterede tilbud og aftaleændringer

Kladder kan redigeres. Ved redigering af Sendt/Afventer vises en advarsel om, at tilbuddet allerede er fremsendt.

Accepterede tilbud har en læsevisning. Korrektion kræver et særskilt valg og en begrundelse. En ændringslog gemmer tidspunkt, begrundelse samt tidligere og nye feltværdier. En databasetrigger afviser opdatering af accepterede tilbud uden tilhørende logregistrering. En korrektion kan ikke ophæve accept eller flytte tilbuddet til et andet forløb.

Kundeopgaver kan fortsat oprettes både direkte og fra et tilbud. Ved tilbudsbaseret oprettelse foreslås titel, omfang, leverancer, forudsætninger og honorarvilkår overført. Oprettelsen kræver fortsat et aktivt klik. Både eksisterende kontrol og databasens entydighedskrav beskytter mod dobbeltoprettelse.

Den oprindelige kundeopgaveaftale gemmes som et snapshot. For allerede eksisterende kundeopgaver gemmes deres tilstand ved migrationen; tidligere, ikke-registrerede ændringer kan ikke rekonstrueres. Det accepterede tilbud forbliver et selvstændigt aftalegrundlag.

En kundeopgave har en enkel liste over aftaleændringer med valgfri dato, beskrivelse, eventuelt nyt honorar samt reference til kundens accept/dokumentation. Angives et nyt honorar her, opdateres kundeopgavens aktuelle honorar i samme transaktion. Den oprindelige aftale og tilbuddet overskrives ikke. Almindelige rettelser i kundeopgaven kræver ikke en aftaleændring; ejeren vælger selv, hvornår en ændring er væsentlig.

### Evaluering og datoer

Kundeopgaver har valgfrie felter til faktisk anvendte timer, genanvendelsespotentiale (Ja/Nej/Ikke vurderet) og en kort note om genanvendelig viden. Resultat/læring og muligt fremtidigt samarbejde er bevaret.

Forretningsmodulets datofelter bruger kalender med dansk datoformat. Tomme datoer forbliver tomme. Historiske datoer kan vælges mellem 1900 og 2100. Dags dato foreslås kun for afsendelsesdato, når tilbuddet markeres Sendt; forslaget kan ændres eller tømmes. Afsluttet status indsætter ikke automatisk en afslutningsdato.

Eksisterende datotekst, som ikke kan læses som ISO-dato, vises og bevares ved lagring, indtil ejeren vælger en kalenderdato. Eksisterende datoer uden for kalenderens interval kræver særskilt vurdering, før de redigeres.

### Brugeroplevelse og opfølgning

- Kompakt tabel med kunde, forløb, status og beslutningsdato samt søgning og filtre.
- Ét valgt forløb med de eksisterende fem faner Pipeline, Tilbud, Kundeopgaver, Deadlines og Afsluttet.
- Oprettelsesformularer er sammenklappede. Aktør er ikke valgt på forhånd ved oprettelse.
- Eksisterende tilbud og kundeopgaver viser først deres oplysninger i læsevisning. Redigering og sekundære oplysninger foldes ud efter behov.
- Tilknyttede åbne opfølgninger vises over forløbets faner med handling, person, status og dato. Afventer vises tydeligt uden at gætte, hvem der har ansvaret.
- Dashboardets opfølgninger viser nu deres tilknyttede forløb og kan åbne det direkte.
- Møder og opfølgninger genbruges fortsat via id-koblinger. Ingen parallel næste-handling-registrering er oprettet.

Tilbud og kundeopgaver viser samme forløbs opfølgninger. En særskilt ansvarlig og præcis opdeling mellem kundens og Franks handlinger kan eventuelt tilføjes senere; den kan ikke udledes pålideligt af de nuværende statusser.

### Visuel identitet

Den synlige produkt- og browsertitel er **FBM Advisory Dashboard** med den diskrete version **3.0 – udviklingsversion** og den ønskede undertitel. Accentfarven er afdæmpet grøn, teksten blågrøn og fladerne lyse. Udviklingsdatabasen markeres fortsat tydeligt.

Der blev ikke fundet kompaslogo, designmanual eller andre billed-/designaktiver i projektet. Derfor anvendes en neutral midlertidig tekstidentitet. Til præcis brandtilpasning mangler kompaslogo som SVG eller transparent PNG samt gældende designmanual med farver og typografi.

Projektets startvinduetitler er opdateret. Skrivebordet er ikke ændret. Ejerens genvej kan senere omdøbes til FBM Advisory Dashboard; et nyt ikon kræver et godkendt ikon/logo og ændres via genvejens egenskaber.

## Database, sikkerhed og migration

Migration **005_agreement_details** tilføjer honorarvilkår, evalueringsfelter, oprindelig aftale, `proposal_changes`, `engagement_amendments` og beskyttelsestrigger. Ingen historiske honorarbeløb omskrives.

Den almindelige migrationsmekanisme tager og verificerer backup inden opgradering. Migrationen er afprøvet på en isoleret database i version 4 samt friske testdatabaser. Alle browserkontroller bruger syntetiske data i `.stage4-test-data/browser`.

**Driftsoverførsel er spærret:** `init_db()` stopper i produktionstilstand før skrivehandlinger, når migration 005 afventer. Den nye kode må derfor afprøves via udviklingsstarten. Godkendelse af etape 4 og en særskilt, kontrolleret frigivelse til drift er nødvendig. Der er ikke skiftet gren eller ændret på `main`.

Der er ikke foretaget eksterne AI-kald eller scraping under udvikling og test. Ingen nye Python-afhængigheder er tilføjet.

## Testresultater

Automatisk kommando: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.

**28 tests bestod**, herunder eksisterende regressionstest og følgende etape 4-kontroller:

| Område | Verifikation |
| --- | --- |
| Honorar | Tomt, eksplicit nul, positivt beløb, forkert talformat, fast pris, timepris, timeloft, honorarloft og retainer |
| Reaktiv formular | Oprettelse gennem Streamlit AppTest med reelt modelskift og lagring af fast pris og timepris |
| Tilbudsbeskyttelse | Kladde/sendte tilbud kan rettes; accepteret tilbud afviser almindelig opdatering; korrektionslog indeholder før/efter |
| UI-korrektion | Valg af korrektionsfunktion, beløbsrettelse og begrundelse samt lagret log |
| Kundeopgaver | Accept, overførte vilkår, afvisning af dobbeltoprettelse og ændring uden overskrivning af tilbud |
| Aftaleændring | Ændring af honorar med acceptreference og bevaret oprindelig aftale, også for direkte opgaver |
| Læring | Faktiske timer, genanvendelsespotentiale og noter |
| Datoer | Tomme datoer samt historisk dato; UI gemmer ikke automatiske gyldigheds- eller afsendelsesdatoer ved kladde |
| Relationer | Eksisterende aktør-, kontakt-, møde- og opfølgningsflows samt afvisning af koblinger på tværs af aktører |
| Database | Integritet, foreign-key-kontrol, version 4-opgradering, bevaret nulbeløb, backup og isoleret gendannelse |
| Ren visning | Ingen ændringer i tilbud ved indlæsning; ingen forhåndsvalgt aktør |
| Driftsspærre | Produktion stopper før oprettelse af mapper eller anden databaseskrivning ved afventende etape 4-migration |

Browserkontrol: desktop **1440 × 1000** og mobil **390 × 844**. Kontrolleret navn/version, udviklingsmarkering, læsevisning, tomt honorar, accepteret tilbud, reaktivt modelskift og synlige kalenderfelter. Ingen vandret sideoverflow og ingen fejl/advarsler i browserloggen. Streamlits indbyggede kalender- og tabelværktøjer kan vise enkelte engelske hjælpetekster afhængigt af browserens sprog.

## Rollback

Testen opretter en version 4-database, opgraderer den gennem normal migrationskode, kontrollerer backup og gendanner denne i en isoleret midlertidig mappe. Tabellernes rækketal i den gendannede version matcher før opgradering.

Ved behov for rollback af en udviklingsdatabase: stop appen, bevar den nuværende database separat, anvend backup fra umiddelbart før migration 005, og start med kodeversion `ef0b38b`. Tilbageførsel til denne backup mister ændringer foretaget efter backupdatoen; disse må bevares separat før gendannelse. Den tidligere kode bør ikke skrive direkte i en database med migration 005, fordi den ikke kender korrektionsloggen og beskyttelsestriggeren.

## Driftsdatabase

Driftsdatabasen er ikke brugt til tests, migrationer eller SQLite-forbindelser. Dens SHA-256 blev læst før og efter arbejdet og var identisk:

`B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`

## Afgrænsninger og næste godkendelse

- Ingen fakturering, bogføring, egentlig tidsregistrering eller rentabilitetsberegning.
- Ingen nyt hovedmodul, hosting, scraping eller AI-udvikling.
- Ingen automatisk rettelse af tidligere nulbeløb eller genskabelse af ukendt aftalehistorik.
- Ingen desktopændringer eller opfundet kompaslogo.
- Drift er ikke opgraderet. Senere driftsoverførsel kræver godkendelse.

Etape 4 afsluttes her. Yderligere udvikling afventer ejerens godkendelse.
