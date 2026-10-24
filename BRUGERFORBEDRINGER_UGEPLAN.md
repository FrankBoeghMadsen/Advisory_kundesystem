# Brugerforbedringer og enkel ugeplanlægning

Aflevering 25. oktober 2026. Udgangspunkt: `e8acb8c` på
`codex/dashboard-3-foundation`. Denne etape omfatter alene den særskilt godkendte
leverancerettelse, acceptdokumentation, kompakt dashboard og enkel ugeplanlægning.
Det er ikke implementering af de udskudte projektøkonomiske etaper eller drift.

## Gennemførte forbedringer

### Leverancer

Oprettelsesformularen genbrugte samme widgetnøgler ved hver lagring. En separat
formulargeneration pr. kundeopgave giver nu tom titel, beskrivelse, deadline og
ansvarlig/note samt status Ikke startet og prioritet Middel efter vellykket
oprettelse. Valideringsfejl nulstiller ikke indtastningen. Redigering beholder
leverancens stabile ID og gemte værdier. Flere leverancer får selvstændige poster.
Én samlet kundeopgave med flere særskilt styrbare leverancer bevares.

### Acceptdokumentation

Acceptdato, acceptform, dokumentreference og kort note kan registreres ved
konvertering fra tilbud til kundeopgave. Oplysninger er valgfrie; manglende
oplysninger vises som ikke angivet, uden at der opfindes dato eller dokumentation.
Der kræves fortsat en aktiv brugerhandling for at oprette kundeopgaven.

Ved accepterede tilbud vises dokumentationen, og Supplér acceptdokumentation
foreslår de senest gemte oplysninger. Ændringer gemmes som nye registreringer;
tidligere registreringer bevares. Uændrede oplysninger dubleres ikke. Allerede
registreret accept genbruges ved senere oprettelse af kundeopgaven og indgår i
øjebliksbilledet af det oprindelige aftalegrundlag. Senere dokumentationsændringer
omskriver ikke dette øjebliksbillede eller aftalte honorarer. Seneste dokumentation
kan også ses under kundeopgavens Oprindelig aftale, særskilt fra oprindelige oplysninger.

Dokumentreference er tekst, ikke upload, filkontrol eller dokumentarkiv.
Et registreret filnavn betyder ikke, at dokumentets indhold er verificeret.

### Dashboard

Datoen vises på dansk og beregnes i Europe/Copenhagen, inklusive sommertid.
Aktiviteter vises i kompakte, uindrammede rækker med dato, titel, status og Åbn.
Rød dato og teksten Overskredet frist markerer passerede bindende frister.
Orange markerer frister i dag og de næste tre kalenderdage. Høj prioritet er
fremhævet med fed skrift. Afsluttede/annullerede leverancer vises ikke som
overskredne. Forventede beslutningsdatoer bevarer deres tydelige ikke-bindende
betydning og får ikke den røde deadline-markering. Ingen animation.

### Ugeplan

Dashboard → Ugeplan viser mandag–søndag, markering af i dag og ugeskift.
Dagene fordeler sig responsivt over flere rækker, så normale vinduer ikke giver
syv ulæseligt smalle kolonner. En bred skærm kan vise flere dage på samme række.

Arbejdsblokke har dato, kundeopgave eller leverance, kort beskrivelse, planlagte
timer og note. Ét mål vælges aktivt; leverancens kundeopgave valideres. En tom
beskrivelse får målets titel. En leverance kan fordeles på flere blokke/dage.
Blokke kan redigeres og slettes med bekræftelse. Sletning ændrer ikke opgave,
leverance eller økonomi. Formularen lukkes og nulstilles efter vellykket gemning.

Standardkapaciteten er 7 timer mandag–fredag og 0 i weekenden. Dagskapacitet kan
ændres, også til nul eller højere værdier. Overbelastning giver en advarsel, men
blokering indføres ikke. Planlagte timer opbevares som hele minutter for at undgå
afrundingsdrift. Gyldige positive timer accepteres uden et syvtimersloft.

Åbne leverancedeadlines vises særskilt i ugen og kan åbnes direkte. De reserverer
ingen arbejdstid. En arbejdsblok efter den tilknyttede åbne leverances deadline
markeres. Planlægning ændrer ikke deadlines, leverancestatus eller honorarer.

## Migration og sikkerhed

Migration **9 – planning_acceptance** er additiv:

- `proposal_acceptances`: acceptoplysninger og append-only registreringshistorik.
- `work_blocks`: planlagte arbejdsblokke og eksisterende opgave-/leverancerelationer.
- `daily_capacity`: eksplicitte kapacitetsafvigelser pr. dato; standarder beregnes uden seeding.

Ingen eksisterende forretningsrækker eller kolonner ændres ved migrationen.
Målrettede SQLite-triggers og servicevalidering beskytter nye relationer og
acceptregistreringer, også når global FK-håndhævelse er slået fra. Den tidligere
globale FK-risiko er ikke ændret for resten af databasen.

Eksisterende backup før migration, integritetskontrol og foreign_key_check bevares.
Udviklingsstarten tilføjer `FRANK_MONITOR_PLANNING_MIGRATION=1`. En gammel
Streamlit-session uden dette flag stopper før migration 9; genindlæsning alene
må ikke migrere udviklingsdata. Produktionsspærren bevares og omfatter også 9.
Driftsstartfil, lokal netværksbinding og AI-sikkerhed er uændrede.

Al udført udvikling og test anvendte isolerede syntetiske databaser.
Den eksisterende `.dev-data` er ikke migreret af agenten i denne etape.
Den migreres først ved brugerens genstart af udviklingsversionen, med backup.
Driftsdatabasen er ikke åbnet via SQLite eller ændret. SHA-256 før og efter:
`B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.
`main` er fortsat `ea7b6dd9151d1d412ba427f938f8b0659e28512c` og er ikke ændret.

### Tilbageførsel

Stop udviklingsserveren først. Bevar den aktuelle version 9-database med nye
planlægningsdata som separat kopi. Brug derefter den tidligere kodeversion sammen
med den verificerede pre_migration-backup fra version 8 i et isoleret miljø.
Kontrollér backup, integritet og historik, før en startkonfiguration ændres.
Der er ikke implementeret destruktiv nedgradering af skemaet. Tilbageførsel til
backup medtager ikke senere registreringer; disse må bevares/overføres særskilt.
Dette er en tilbageførselsvejledning, ikke godkendelse til ændring af drift.

## Tests

Kommando: `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`

**58 tests bestået**, herunder seks nye testforløb med mange delkontroller:

- Leveranceformular nulstilles efter to oprettelser; tidligere leverancer bevares.
- Redigeringsværdier og standarder, acceptlagring og -visning i Streamlit AppTest.
- Accept indgår i oprindelige snapshots, supplering bevarer honorarer/snapshots,
  tidligere accept genbruges, og dubletkundeopgave fra samme tilbud afvises.
- Ugyldig acceptdato ændrer ikke tilbudsstatus eller opretter kundeopgave.
- Arbejdsblokke oprettes, flyttes, redigeres og slettes; samme leverance på flere dage.
- Dags- og ugekapacitet, weekendændring, nulkapacitet, overbelastning uden blokering,
  adskillelse af deadline og arbejdsdag samt advarsel ved arbejde efter deadline.
- Ugyldige tal/datoer og relationer afvises. Leverede leverancer er ikke overskredne.
- Dansk dato omkring UTC-døgnskift og lokal tidszone.
- Udviklingsgenindlæsningsspærre og produktionsspærre ved ventende migration 9.
- Version 8 → 9 med backup og gendannelsestest, bevaret eksisterende registrering
  samt integritets- og relationskontrol.

Tidligere regressionstests er bevaret. Forventet skemaversion er opdateret fra
8 til 9. En ældre navigationstest brugte et møde den 24. oktober 2026 som et
kommende møde; testdatoen er gjort relativ til lokal dags dato, så den ikke
fejler alene fordi testdagen nu er senere. Mødefiltrering er ikke ændret.

En konkret browsertestdatabase startede på version 8. Output bekræftede:
backupversioner 1–8, restore `ok`, aktuel version 1–9 og integrity `ok`.
Backup ligger i den isolerede testdatabases Backups-mappe, ikke i drift.

Browserkontrol i Edge på testport 8520 bekræftede dansk dags dato, kompakte
deadline-rækker med rød/orange markering, ugekapacitet og overbelastning,
oprettelse af en tre timers blok med kvittering og genberegning, synlig
acceptdato/-form/-reference samt genbrug ved eksplicit oprettelse af kundeopgave.
Layout blev gennemset ved effektive bredder ca. 1285, 854 og 434 px uden vandret
dokumentoverløb. Viewportanmodningerne var henholdsvis normal desktop, 768 og
390 px; browserzoom påvirkede de effektive bredder. Ingen fysisk iPad-test.
Ingen applikationsfejl blev observeret i browserloggen; de registrerede fejl
kom fra browserens annonceblokeringsudvidelse. Den midlertidige testserver er stoppet.

## Afgrænsninger og senere Outlook

- Kapacitet omfatter kun gemte arbejdsblokke. Møder, Outlook, privat tid og andre
  kalenderaftaler fratrækkes endnu ikke automatisk. Timerne er planlagte, ikke faktisk tidsforbrug.
- Ugetotalen er netto for hele den valgte uge, inklusive allerede passerede dage.
  En ledig ugetotal ophæver ikke en dags overbelastning; begge dele vises.
- Ingen autoestimering af resterende arbejdsindsats eller automatisk vurdering af,
  om en deadline er realistisk. Se planlagte timer, frist og efter-deadline-advarslen.
- Ingen tidsregistrering, fakturering, filupload, nye overvågnings-/AI-kald eller Outlook-forbindelse.

UI, databaseadgang og ren kapacitetsberegning er adskilt i `views/planning.py`
og `services/planning_service.py`. En senere læseadapter kan levere normaliserede
optaget-intervaller til beregningen uden at omskrive aftale-/leverancemodellen.
Adapteren skal samle overlappende intervaller før fradrag og respektere free/busy.
Arbejdstidsvinduer, heldagsaftaler og sammenhæng med arbejdsblokke kræver særskilt
designbeslutning. Ingen Graph-appregistrering, tokens eller kalenderadgang er etableret.

## Praktisk prøvevejledning

1. Genstart via `Start Monitor Development.bat`, ikke driftsstarten. Kontrollér
   UDVIKLINGSDATABASE. En gammel udviklingssession kan vise et sikkerhedsstop,
   indtil den genstartes. Første start tager backup og anvender migration 9.
2. Under en syntetisk kundeopgave oprettes to forskellige leverancer. Kontrollér
   tomme oprettelsesfelter efter hver gemning og bevarede værdier i redigering.
3. Opret et TEST-tilbud og brug Opret kundeopgave fra tilbud. Angiv acceptdato,
   E-mail, et TEST-filnavn og eventuel note. Kontrollér oplysningerne både under
   tilbuddet og kundeopgavens Oprindelig aftale. Supplér dokumentation og kontrollér historikken.
4. Dashboard → Overblik: kontrollér dags dato. Giv åbne TEST-leverancer en
   passeret og en nært forestående dato. Kontrollér rød/orange markering og Åbn.
   Markér en leverance Leveret; den må ikke længere stå som overskredet.
5. Dashboard → Ugeplan: skift til næste uge. Opret to blokke for samme leverance
   på forskellige dage og kontrollér timerne pr. dag og samlet for ugen.
6. Planlæg ni timer på en hverdag. Gemningen skal lykkes med overbelastningsadvarsel.
   Planlæg to timer i weekenden; sæt derefter dagens kapacitet til fire timer.
7. Redigér en blok, og slet den derefter med bekræftelse. Opgave og leverance skal
   stadig eksistere. Åbn igen Opret arbejdsblok; tidligere tekst må ikke stå der.
8. Kontrollér deadlines i kalenderen og en blok efter leverancens frist. Fristen
   må ikke i sig selv bruge kapacitet. Prøv også ugeplanen i et smallere vindue.

Stop efter denne etape. Outlook og drift kræver fortsat særskilt beslutning.
