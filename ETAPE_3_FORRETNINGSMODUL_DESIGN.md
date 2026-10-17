# Etape 3 - design af forretningsmodul

## Formål og afgrænsning

Etape 3 skal give Frank Advisory et enkelt arbejdsredskab til at følge en konkret rådgivningsmulighed fra identificeret behov til tilbud, kundeopgave, leverancer og afslutning.

Designet bygger på disse principper:

- En relation er ikke automatisk en salgsmulighed.
- En aktør kan have flere samtidige forretningsforløb.
- Tilbud og kundeopgaver knyttes til et konkret forretningsforløb, ikke kun til aktøren.
- Eksisterende kontakter, møder og opfølgninger genbruges frem for at blive registreret igen.
- Overgange mellem trin foretages aktivt af brugeren.
- Fakturering, bogføring og egentlig økonomistyring er ikke en del af modulet.

Dette dokument er alene et beslutningsoplæg. Der er ikke ændret kode, database eller kundedata.

## Forudsætning: isoleret udviklingsdatabase

Inden implementering anbefales en fail-closed adskillelse mellem aktiv drift og udvikling:

1. Startfilen til daglig brug angiver eksplicit `FRANK_MONITOR_MODE=production` og den aktive datamappe.
2. En særskilt udviklingsstart angiver `FRANK_MONITOR_MODE=development` og en separat, Git-ignoreret datamappe, eksempelvis `.dev-data`.
3. Direkte start uden angivet tilstand eller datamappe må ikke kunne åbne den aktive database. Programmet skal stoppe med en tydelig fejl.
4. Programmet skal afvise opstart, hvis udviklingstilstand peger på den aktive datamappe.
5. Udviklingstilstand og den anvendte databaseplacering skal vises tydeligt i sidepanelet.
6. En udviklingskopi kan oprettes med en særskilt, manuel kommando via SQLite-backup. Kopieringen må aldrig ske automatisk ved programstart.
7. Automatiske tests skal altid bruge midlertidige databaser og kontrollere, at udvikling ikke kan anvende produktionsstien.

Den aktive database forbliver dermed kun tilgængelig gennem den eksplicitte produktionsstart. Denne sikring bør være første, afgrænsede implementering, før forretningsmodulet påbegyndes.

## Anbefalet begreb

Det centrale objekt kaldes **forretningsforløb**. Det repræsenterer et konkret behov eller en konkret rådgivningsmulighed hos en aktør.

Et forretningsforløb oprettes kun manuelt. En aktør, kontakt eller et møde kan derfor eksistere uden et forretningsforløb.

## Enkel datamodel

| Objekt | Formål | Vigtigste relationer |
| --- | --- | --- |
| Aktør | Eksisterende virksomhed, organisation eller anden aktør | Har kontakter, møder og nul eller flere forretningsforløb |
| Forretningsforløb | Samler ét konkret behov eller én mulighed | Tilhører én aktør; kan have primær kontakt, møder, tilbud og opfølgninger |
| Tilbud | Beskriver et konkret eller revideret tilbud | Tilhører ét forretningsforløb; kan danne grundlag for en kundeopgave |
| Kundeopgave | Den accepterede og udførende rådgivningsopgave | Tilhører ét forretningsforløb; kan være knyttet til et accepteret tilbud |
| Leverance | En afgrænset levering eller milepæl med deadline | Tilhører én kundeopgave |
| Mødekobling | Knytter eksisterende møder til relevant forretningsforløb | Et møde kan ved behov knyttes til flere forløb |
| Opfølgning | Eksisterende opgave/opfølgning | Kan valgfrit knyttes til et forretningsforløb eller en leverance |

Aktørens navn og kontaktoplysninger skal ikke kopieres ind i tilbud eller kundeopgaver. De vises gennem relationen til den eksisterende aktør.

## Vigtigste felter

### Forretningsforløb

- Aktør og valgfri primær kontakt.
- Titel og kort beskrivelse af behovet.
- Valgfrit rådgivningsområde.
- Status og næste forventede beslutningsdato.
- Næste handling, vist via en tilknyttet opfølgning.
- Afslutningsårsag og afslutningsdato, når forløbet lukkes.
- Oprettet og senest ændret.

### Tilbud

- Titel og versionsnummer.
- Omfang, forventede leverancer og væsentlige forudsætninger.
- Honorarmodel: fast pris, timepris, klippekort/retainer eller endnu ikke aftalt.
- Tilbudt honorar ekskl. moms og valgfri honorarnote.
- Ingen fakturering, bogføring eller økonomiberegning.
- Status, afsendelsesdato og eventuel gyldighedsdato.
- Valgfri reference til tilbudsdokument.

### Kundeopgave

- Titel og opgavebeskrivelse.
- Valgfri reference til accepteret tilbud.
- Aftalt honorarmodel, aftalt honorar ekskl. moms og valgfri honorarnote.
- Status, startdato og forventet slutdato.
- Faktisk afslutningsdato.
- Resultat/læring og note om muligt fremtidigt samarbejde.

### Leverance

- Titel og kort beskrivelse.
- Deadline og prioritet.
- Status og leveringsdato.
- Valgfri ansvarlig kontakt eller note.

## Statusser og arbejdsgang

### Statusser

- **Forretningsforløb:** Åben, Afventer, Pauset, Lukket. Ved Lukket vælges årsag: Vundet, Tabt eller Ikke relevant.
- **Tilbud:** Kladde, Klar til afsendelse, Sendt, Afventer, Accepteret, Afvist, Udløbet eller Trukket tilbage.
- **Kundeopgave:** Planlagt, I gang, Afventer, Afsluttet eller Annulleret.
- **Leverance:** Ikke startet, I gang, Afventer, Leveret eller Annulleret.

### Normal arbejdsgang

1. Relationer, kontakter og møder registreres som i dag.
2. Når et konkret behov er identificeret, vælger brugeren aktivt **Opret forretningsforløb**.
3. Et eller flere tilbud kan udarbejdes under forløbet.
4. Når et tilbud accepteres, kan brugeren aktivt vælge **Opret kundeopgave**. Relevante oplysninger foreslås fra tilbuddet, men gemmes først efter godkendelse.
5. Leverancer og deadlines oprettes under kundeopgaven. Opfølgninger kan kobles til forløbet eller en bestemt leverance.
6. Ved afslutning registreres resultat og eventuel mulighed for fremtidigt samarbejde.
7. Et muligt nyt samarbejde bliver først et nyt forretningsforløb, når brugeren aktivt opretter det.

Et historisk opgaveforløb skal kunne registreres direkte som kundeopgave i et nyt forretningsforløb uden først at oprette et tilbud.

## Sammenhæng med eksisterende funktioner

- **Kontakter:** En eksisterende kontakt kan vælges som primær kontakt. Kontaktdata vedligeholdes fortsat ét sted.
- **Møder og referater:** Eksisterende møder kan kobles til et forretningsforløb. Referatet forbliver på mødet.
- **Opfølgninger:** Den nuværende funktion genbruges. En opfølgning kan fortsat stå alene eller få en valgfri kobling til forløb/leverance.
- **Briefinger:** Briefinger kobles fortsat til aktør og møde. Relevant forretningskontekst kan vises gennem mødekoblingen frem for dobbeltregistrering.
- **Dashboard:** Senere kan visninger beregnes ud fra de samme poster, eksempelvis tilbud der afventer, aktive kundeopgaver og kommende deadlines.

## Enkel skitse af brugerfladen

```text
FORRETNING
[Pipeline] [Tilbud] [Kundeopgaver] [Deadlines] [Afsluttet]

Aktør          Forløb                   Fase          Status      Næste dato
Glostrup ...   Rådgivningsbehov A       Tilbud        Afventer    15-11-2026
...

FORRETNINGSPROFIL
Aktør / Forløbets titel                         [Rediger] [Luk]
Status | Primær kontakt | Næste handling | Næste dato

[Overblik] [Tilbud] [Opgave og leverancer] [Møder og opfølgninger]

Overblik
Behov og omfang
Seneste aktivitet
Næste handling
```

På aktørprofilen tilføjes sektionen **Forretning**, som viser aktørens forløb og knappen **Opret forretningsforløb**. Et TMJ-lignende emne kan derfor fortsat have møder og relationer uden at optræde i pipeline.

## Sådan undgås dobbeltregistrering

- Aktør- og kontaktdata refereres med id og kopieres ikke.
- Møder knyttes til forløb; referater kopieres ikke.
- Ét konkret behov oprettes som ét forretningsforløb. Alternative eller reviderede tilbud til samme behov ligger under dette forløb.
- Forskellige behov hos samme aktør oprettes som separate forretningsforløb.
- En accepteret tilbudspost kan genbruges som forslag ved oprettelse af kundeopgaven, men overgangen kræver aktiv godkendelse.
- Deadlines registreres på leverancer. En opfølgning peger på leverancen i stedet for at gentage hele beskrivelsen.
- Dashboard og oversigter beregnes fra grunddata og har ikke deres egne kopier.
- Databasen bør have entydighedskrav for blandt andet tilbudsversion pr. forløb og mødekoblinger.

## De tre illustrative scenarier

- **Nomeco:** Et forretningsforløb kan oprettes historisk med en direkte kundeopgave i status Afsluttet. Resultat og mulig fremtidig relation noteres. Der oprettes ikke automatisk en ny mulighed.
- **Glostrup Apotek:** Hvert særskilt rådgivningsbehov får sit eget forretningsforløb. Flere tilbud kan være Sendt/Afventer samtidig. Reviderede eller alternative tilbud til samme behov ligger under samme forløb.
- **TMJ:** Aktør, kontakt og kommende møde registreres uden forretningsforløb. Først når et konkret behov er identificeret, oprettes forløbet manuelt.

Scenarierne er kun anvendt til at afprøve designet. Der er ikke registreret eller ændret faktiske kundedata.

## Godkendte beslutninger

Ejeren godkendte den 17. oktober 2026 følgende:

1. **Begreb:** Modulet hedder *Forretning*, og det centrale objekt hedder *forretningsforløb*.
2. **Tilbudsøkonomi:** Honorarmodel og tilbudt/aftalt honorar registreres struktureret, men uden fakturering, bogføring eller betalingsstyring.
3. **Afgrænsning af forløb:** Forskellige behov er separate forløb; alternativer eller versioner af samme behov er flere tilbud under samme forløb.
4. **Mødekobling:** Ét møde kan knyttes til flere forretningsforløb.
5. **Overgang til opgave:** Et accepteret tilbud opretter kun en kundeopgave efter en aktiv brugerhandling.
6. **Historiske opgaver:** En kundeopgave kan oprettes direkte uden et forudgående tilbud.
7. **Dokumenter:** Egentlig dokumenthåndtering udskydes; første version har en valgfri dokumentreference.

## Foreslået implementeringsrækkefølge efter godkendelse

1. Etabler og test databaseisoleringen beskrevet ovenfor.
2. Tilføj datamodel og migrationer på en udviklingskopi.
3. Implementér forretningsforløb og kobling til aktør, kontakt, møde og opfølgning.
4. Implementér tilbud og den eksplicitte overgang til kundeopgave.
5. Implementér kundeopgaver, leverancer og deadlines.
6. Tilføj oversigter og relevante dashboarddata.
7. Gennemfør regressionstest og dokumenteret gendannelsestest uden adgang til den aktive database.

Implementeringen er godkendt som etape 3. Resultaterne dokumenteres særskilt i `ETAPE_3_IMPLEMENTERING.md`.
