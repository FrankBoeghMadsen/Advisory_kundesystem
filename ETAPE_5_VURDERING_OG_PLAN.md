# Etape 5 – teknisk vurdering og plan

18. oktober 2026. Trin 1: beslutningsoplæg, afventer godkendelse.

Udgangspunkt: commit `ea09e18` på `codex/dashboard-3-foundation`. Vurderingen bygger på kildekoden og ejerens beskrevne brugertest. Der er ikke åbnet databaser, kørt app/migrationer eller foretaget eksterne kald. Kun dette dokument er tilføjet.

## 1. Konstaterede forhold

| Område | Fund i den aktuelle kode | Konsekvens |
| --- | --- | --- |
| Deadlineoverblik | `views/dashboard.py` beregner Næste 30 dage og Forfaldne udelukkende fra `followups`. Leverancer indgår kun i et separat antal. | Leverancen den 24. oktober vises ikke i 30-dagesoptællingen, selv om den er åben og dateret. Fejlen kan forklares uden adgang til testdatabasen. |
| Møder | Dashboardets mødeforespørgsel begrænser resultatet til otte poster, og tælleren bruger længden af denne liste. | Tallet kan være afkortet og bygger på en anden periode end opfølgningerne. |
| Nøgletal | Forretningstallene er selvstændige SQL-forespørgsler. De enkelte tal har ingen præcis filtreret destination. | Brugeren kan ikke se, hvilke poster et tal dækker. |
| Navigation | `app.py` bruger ét langt radiovalg fra `PAGE_OPTIONS`; overvågningsknappen er altid fremhævet. | Den tidligere overvågningsapp præger stadig den daglige arbejdsgang. |
| Forretningsfaner | `views/business.py` bruger almindelige faner uden tællere. Deadlines viser alle leverancer, også udaterede og afsluttede. | Fanens navn, indhold og forventede optælling stemmer ikke tilstrækkeligt overens. |
| Direkte honorarrettelse | `_engagement_editor()` indlæser honorarfelter; `save_business_record()` tillader opdatering af aftalt honorar og honorarvilkår. | Honoraret kan ændres uden aftaleændring. Det oprindelige snapshot bevares, men en fuld mellemhistorik sikres ikke. |
| Aftaleændringer | `record_amendment()` opdaterer aktuelt honorar straks, hvis nyt honorar er angivet. Tabellen har ingen acceptstatus. | En foreslået ændring kan ikke skelnes fra en accepteret ændring. |
| Beløbsformat | Parseren accepterer tal, dansk gruppering og decimalkomma, men ingen valutaendelse. | `25.000 kr.` afvises, mens `25.000` accepteres. |
| Tomme valgmuligheder | Koblingsfelter oprettes også med tomme lister. | Streamlits engelske standardtekst kan vises. |

## 2. Dashboard med tre områder

### A. Opmærksomhed og kommende aktiviteter

Forsidens primære område bliver én kronologisk arbejdsliste med forfaldne aktiviteter øverst og derefter i dag til og med 30 dage frem. Dagens dato beregnes i dansk tidszone.

Genbrug følgende eksisterende data:

- Åbne leverancers `due_date`, med aktør og kundeopgave via eksisterende relationer.
- Kommende møders `meeting_date` og eventuelle klokkeslæt.
- Åbne opfølgningers `due_date`.
- Tilbuddenes gyldighedsdato og forløbenes forventede beslutningsdato, når den pågældende post stadig er relevant. Beslutningsdato betegnes som forventet beslutning, ikke som bindende deadline.

Rækkerne viser dato, kunde, titel, type, status og eventuel prioritet samt en Åbn-handling. Ingen kunstig prioritet tilføjes til poster uden prioritet.

En lille fælles funktion i servicelaget samler aktiviteterne. **Listen, Forfaldne og Næste 30 dage beregnes fra præcis samme datasæt og filtre**, før eventuel visningsbegrænsning. Forfaldne tælles særskilt; Næste 30 dage er fra i dag til og med dag 30 og omfatter også dagens aktiviteter.

Regler:

- Leverancer i Leveret/Annulleret og opfølgninger i Lukket/Arkiveret udelades.
- Leverancer under afsluttede/annullerede kundeopgaver udelades fra den aktive arbejdsliste. Åbne restleverancer i sådanne opgaver vises i en lille datakontrol-liste, så de ikke skjules permanent.
- Tilbudsfrister medtages kun for Sendt/Afventer; beslutningsdatoer kun for Åben/Afventer. En Pauset post bliver dermed ikke automatisk en akut handling.
- Udaterede poster medtages i relevante åbne oversigter, men tælles ikke som daterede aktiviteter. Fri datotekst, som ikke kan fortolkes sikkert, bevares og markeres til afklaring.
- Et tidligere møde er ikke automatisk forfaldent: mødemodellen har ingen sikker gennemført-status. Kun kommende møder indgår; gammel mødedato kan ikke i sig selv skabe en forfalden handling.

**Dobbeltregistrering:** En aktivitet identificeres med type og id, ikke titel. Samme møde optræder kun én gang, selv om det er knyttet til flere forløb. Flere joins må ikke multiplicere en leverance eller opfølgning. En reel opfølgning og en leverancedeadline er ikke automatisk samme handling, blot fordi de er koblet. En koblet opfølgning uden selvstændig næste handling og med samme dato som leverancen samles under leverancerækken; selvstændige handlinger eller forskellige datoer bevares. Denne regel skal være ens i liste og tællere og testes særskilt.

Eksempel fra brugertesten: Med dato 18. oktober 2026 og en åben, aktiv leverance den 24. oktober skal leverancen fremgå af listen og bidrage med én til Næste 30 dage. En opfølgning, der kun gentager samme deadline efter ovenstående regel, må ikke fordoble tallet.

### B. Klikbare nøgletal

| Betegnelse | Foreslået præcis definition | Destination |
| --- | --- | --- |
| Aktive kunder | Unikke aktører med mindst én kundeopgave i Planlagt/I gang/Afventer. Ikke alle aktive aktørprofiler. | Kundeliste med de aktive opgaver |
| Åbne forretningsforløb | Forløb i Åben/Afventer. Pausede kan vises via særskilt filter. | Filtreret forløbsoversigt |
| Tilbud afventer svar | Tilbud i Sendt/Afventer | Filtreret tilbudsoversigt |
| Aktive kundeopgaver | Opgaver i Planlagt/I gang/Afventer | Filtreret kundeopgaveoversigt |
| Åbne leverancer | Leverancer i Ikke startet/I gang/Afventer under aktive kundeopgaver, også uden dato | Filtreret leveranceoversigt |
| Åbne opfølgninger | Opfølgninger uden Lukket/Arkiveret, også uden dato | Filtreret opfølgningsoversigt |

Nøgletal præsenteres som kompakte knapper med antal og navn. Deres destinationslister bruger samme forespørgsler/statusdefinitioner som tallene. Et nøgletal kan åbne en liste på tværs af kunder; det må ikke blot vælge det første forløb.

### C. Kunder og næste forretningsskridt

Et mindre område viser aktive kunder/opgaver og et begrænset udvalg af afventende tilbud og åbne muligheder. Eksisterende næste handling, dato og person genbruges fra koblede opfølgninger. Vis eksempelvis højst fem rækker og adgang til den fulde oversigt.

Der er ikke grundlag for at beregne en intelligent salgsprioritet eller automatisk udpege muligheder. Vis dokumenterede åbne forløb; kunder med tidligere afsluttede opgaver kan mærkes som eksisterende relationer uden at blive talt som aktive kunder.

Signalpåmindelse, LinkedIn-referencekilder og store signalstatusbokse fjernes fra forsiden. Manuel observationsregistrering og kildereferencer bevares på de relevante eksisterende sider. Den manuelle overvågningsknap flyttes ind under overvågning.

## 3. Kortere menu og direkte åbning

Bevar de nuværende renderfunktioner og interne sidenavne. Tilføj et tyndt navigationslag med to gruppeoverskrifter:

```text
DAGLIGT ARBEJDE
  Dashboard
  Forretning
  Møder og opfølgninger
  Kontakter og virksomheder

VIDEN OG MULIGHEDER
  Observationer
  Viden
  Regulatorisk overvågning
```

Under Møder og opfølgninger vælges Møder eller Opfølgninger; den eksisterende Opgaver-visning genbruges og omdøbes synligt. Under Kontakter og virksomheder vælges den eksisterende kontakt- eller aktørvisning. Under Regulatorisk overvågning findes Signalindbakke, Kilder, Triggerregler og Briefing. Briefing får fortsat direkte genveje fra møder, så forberedelse ikke kræver en omvej gennem overvågning.

Anbefaling: grupperede knapper i sidepanelet og ét lokalt radiovalg på samlesiderne. Det understøtter eksisterende `session_state`-navigation uden en omlægning til nye sidefiler eller afhængigheder. Gamle interne destinationer oversættes til den korrekte hovedgruppe og underside.

Udvid navigationshjælperne med mål-id og ønsket visning. En dashboardleverance skal åbne **den konkrete kundeopgave/leverance**, markere den og vælge korrekt fane; et møde skal åbne det konkrete møde. Filtre, som ellers skjuler målet, nulstilles kontrolleret. Nøgletal åbner derimod hele den præcist filtrerede mængde.

Forretningsfanerne får mere afstand, rolig baggrund/adskillelse og tydelig aktiv markering. Tællere for Tilbud og Kundeopgaver viser antal poster i det valgte forløb. Deadlines tæller og viser kun åbne, gyldigt daterede leverancer under aktive kundeopgaver i forløbet, også datoer mere end 30 dage frem. Alle leverancer kan fortsat findes under kundeopgaven. Afsluttet tæller afsluttede/annullerede kundeopgaver. Fanetal og indhold beregnes sammen.

## 4. Tilbud, aftalegrundlag og honorarhistorik

Den beskrevne testkæde håndteres aktuelt således ifølge koden:

| Hændelse | Nuværende lagring/effekt |
| --- | --- |
| Tilbud på 0 kr. | `proposals.offered_fee_ex_vat` gemmer eksplicit nul. |
| Kundeopgave aftales til 2.700 kr. | Kundeopgaven gemmer 2.700; `original_agreement` fastholder den oprindelige opgaveaftale. |
| Accepteret tilbud korrigeres til 20.000 kr. | Tilbudsbeløbet ændres; korrektionsloggen indeholder før/efter og begrundelse. Kundeopgavens beløb og snapshot ændres ikke. |
| Aftaleændring til 25.000 kr. | Ændringen gemmes med før/efter; kundeopgavens aktuelle honorar bliver straks 25.000. Der findes endnu ingen acceptstatus. |
| Honorar rettes direkte i kundeopgaven | Kan i dag ske uden en aftaleændring. Dette er den væsentligste historikmangel. |

Det er altså muligt og korrekt, at et korrigeret tilbud viser 20.000, den oprindelige opgaveaftale viser 2.700 og det aktuelle honorar viser 25.000. De repræsenterer forskellige registreringer/hændelser, ikke én værdi, som skal synkroniseres automatisk. Testposterne er ikke undersøgt direkte i databasen.

### Anbefalet beskyttelse

- Tilbudskorrektioner forbliver begrundede rettelser med log. De ændrer aldrig automatisk en kundeopgave eller udgør en ny kundeaftale.
- Ved ny accept/oprettelse gemmes også et låst snapshot af det accepterede tilbud på kundeopgaven. Dermed kan både tilbudsgrundlaget ved accept og den oprindeligt aftalte opgavepris genfindes efter senere registreringskorrektioner.
- Aktuelt honorar vises udtrykkeligt som **Aktuelt aftalt honorar**, med korrekt enhed ved timepris. Tomt honorar og nul bevares som forskellige værdier.
- Efter oprettelse fjernes honorar og bindende honorarvilkår fra almindelig opgaveredigering. Servicelaget skal ligeledes afvise ændringer ad denne vej. Beskyttelsen må ikke kun være et skjult felt i brugerfladen.
- Nye aftaleændringer har status **Foreslået** eller **Accepteret**. Foreslået er standard og påvirker ikke gældende honorar. Accept er en aktiv registrering af kundens accept, ikke elektronisk aftaleindgåelse.
- Accept gemmer tidspunkt, før/efter og dokumentreference i én transaktion. Samme ændring må kun få effekt én gang. Uaktuelle forslag kan ikke ved accept overskrive en nyere accepteret aftale ubemærket; ejeren skal først bekræfte det opdaterede udgangspunkt.
- Accepterede ændringer bliver historik; de rettes ikke stiltiende. En ny ændring kan dokumentere en efterfølgende korrektion.
- Honorarmodel, timeloft, honorarloft og inkluderede timer skal følge samme aftalevej som beløbet. Ingen parallel redigeringsvej for bindende vilkår.

### Eksisterende historik

Eksisterende aftaleændringer har allerede haft effekt. De må ikke automatisk ommærkes til Foreslået, trækkes tilbage eller præsenteres som dokumenteret accepterede.

Anbefaling: vis dem som **Tidligere registreret – acceptstatus ikke registreret**, bevar deres oprindelige oplysninger og økonomiske effekt, og fasthold det aktuelle honorar som udgangspunkt ved migrationen. De to nye statusvalg gælder nye ændringer. Et gammelt acceptgrundlag kan efterfølgende dokumenteres eksplicit uden at ændringen anvendes igen.

Eksisterende snapshots og korrektionslog bevares. Manglende historiske snapshots må ikke udfyldes med det aktuelle, korrigerede tilbud og kaldes oprindelige. Hvor grundlaget ved accept ikke sikkert kan rekonstrueres, skal det fremgå som ikke særskilt registreret. Direkte honorarrettelser fra tiden før forbedringen kan ikke nødvendigvis genskabes og må ikke opfindes.

## 5. Opdeling af kundeopgaven og dansk indtastning

Tre adskilte redigeringsområder genbruger de eksisterende felter:

1. **Redigér kundeopgave:** titel, aktuel beskrivelse, status og datoer. Aktuel arbejdsbeskrivelse kan udvikles, mens oprindeligt aftalegrundlag bevares.
2. **Aftaleændringer:** ændret aftaleomfang, honorarvilkår, dokumentation, accept og historik.
3. **Evaluering:** timer, genanvendelsespotentiale, noter, resultat/læring og fremtidigt samarbejde, med egen Gem-handling.

Beløbsparseren udvides til en valgfri, afsluttende dansk valutaendelse `kr.`/`kr` og eventuelt DKK, kun i beløbsfelter. Timer accepterer ikke valutaendelser. `25000`, `25.000`, `25.000,00` og `25.000 kr.` bliver alle 25.000. Tomt er fortsat manglende, og `0 kr.` er eksplicit nul. Tvetydige/forkerte tal som `25.00`, `25,000`, negative tal og ekstra tekst afvises fortsat.

Tomme koblingslister vises med dansk tekst som Ingen opfølgninger registreret og uden et tomt multiselect. Giv danske placeholders, hvor Streamlit understøtter det. Indbyggede kalender-/tabeltekster, som ikke kan oversættes via eksisterende API, håndteres uden skrøbelige DOM- eller CSS-teksttricks og dokumenteres som en begrænsning.

## 6. Migration og afgrænset implementeringsrækkefølge

Dashboard, tællere, filtrering, menu, fanemarkering, evaluering og beløbsparser kan forbedres med de eksisterende tabeller. Der er ikke brug for et nyt CRM eller en ny aktivitetsdatabase.

Én additiv **migration 006** forventes nødvendig til acceptstatus/-tidspunkt og vilkårsændringer på `engagement_amendments`, låst tilbudssnapshot samt bevaret gældende aftale ved opgradering på `engagements`. Brug eksisterende snapshot-/logmønster; tilføj kun felter, der kræves for ovenstående historik. Tidligere migrationer omskrives ikke.

Efter godkendelse foreslås denne rækkefølge:

1. Fælles aktivitetsgrundlag, konsistente tidsvinduer og klikbare nøgletal.
2. Kortere menu, bevarede genveje og direkte åbning af konkrete poster.
3. Migration 006 og accepterede aftaleændringer med bevaret eksisterende historik.
4. Opdeling af kundeopgaveformularen, tydeligere faner og dansk beløbsindtastning.
5. Regressionstest, browserkontrol og dokumenteret aflevering på udviklingsgrenen.

Alle migrationer og tests foretages på isolerede kopier/testdata. Der tages verificeret backup før migration, og gendannelse til tilstanden før migration afprøves. Driftsdatabasen og den eksisterende driftsspærre bevares. Ingen eksterne kald eller scraping.

## 7. Testplan og udskudte forhold

Test især den konkrete leverancedato 24. oktober set fra 18. oktober, forfaldne datoer, i dag, dag 30 og dag 31; udaterede/afsluttede/annullerede poster; samme møde på flere forløb; koblede leverancer/opfølgninger; samt at hvert tal åbner præcis den mængde, der tælles.

Test direkte navigation fra dashboard til konkret møde, opfølgning, kundeopgave og leverance, også efter at modstridende filtre tidligere har været valgt. Test alle hidtidige sider gennem den nye gruppering.

Brug syntetiske data til kæden **0 → 2.700 → tilbudskorrektion 20.000 → accepteret aftaleændring 25.000**. Kontroller oprindelig og aktuel aftale, korrektionslog, forslag uden accept, ændring uden nyt beløb, afvisning af direkte honorarrettelse og dobbeltaccept samt bevarelse af eksisterende aftaleændringers effekt. Test beløb med valutaendelse separat fra timer.

Test migration, integritet, foreign keys og rollback samt desktop-/mobilvisning. Først i trin 2 køres disse tests; der fremlægges ikke nye testresultater for endnu ikke implementeret kode i dette oplæg.

Udskyd automatisk overvågning, AI-vurdering, økonomiberegninger, egentlig kontraktstyring, ny grafisk identitet og yderligere teknisk ombygning. Et eventuelt mødestatusfelt og mere detaljeret opgaveansvar kan vurderes senere.

## Beslutninger til godkendelse

- Godkend de foreslåede definitioner af nøgletal, perioder og Deadlines-fanen, herunder aktive kunder som aktører med aktive kundeopgaver.
- Godkend den grupperede menu og genbrug af eksisterende visninger.
- Godkend, at aftalte honorarvilkår efter oprettelse kun ændres via aftaleændringer, og at nye forslag først får effekt efter eksplicit accept.
- Godkend den konservative behandling af ældre aftaleændringer uden registreret acceptstatus. Dokumentreference anbefales ved ny accept, men en tom reference må ikke fremstilles som dokumenteret kundegodkendelse.

Der er ikke påbegyndt implementering. Trin 2 afventer ejerens godkendelse.
