# Etape 5 – aflevering og praktisk prøvevejledning

18. oktober 2026. Arbejdet er udført på `codex/dashboard-3-foundation` efter godkendelse af trin 1. Ingen driftsoverførsel er foretaget.

## Gennemførte forbedringer

- Dashboardets primære område er en kronologisk liste over aktiviteter fra i dag til 30 dage frem samt passerede datoer øverst. Leverancer, møder, opfølgninger, tilbudsfrister og forventede beslutninger er tydeligt adskilt.
- Forventede beslutninger betegnes som forventninger, ikke bindende deadlines. Historiske møder bliver ikke automatisk forfaldne.
- Leverancer tælles nu med i periodens aktiviteter og kan åbnes direkte i deres kundeopgave med den valgte leverance foldet ud.
- Seks kompakte, klikbare arbejdsoversigter bruger samme datagrundlag som deres antal: aktive kunder, åbne forløb, afventende tilbud, aktive kundeopgaver, åbne leverancer og åbne opfølgninger.
- Samme møde/leverance multipliceres ikke gennem koblinger. En opfølgning på samme leverance og dato uden særskilt næste handling samles under leverancen, men kan stadig åbnes. Selvstændige handlinger bevares.
- Signalpåmindelser og LinkedIn-referencebokse er fjernet fra forsiden. Eksisterende observations-, kilde-, briefing- og overvågningsfunktioner er bevaret.
- Venstremenuen har nu grupperne Dagligt arbejde og Viden og muligheder med syv hovedvalg. Eksisterende visninger ligger som undervalg. Opfølgninger er adskilt sprogligt fra kundeopgaver.
- Forretningsfanerne er gjort til en tydelig vandret områdevælger med aktiv markering og tællere. Valget fastholdes efter lagring. Deadlines viser kun åbne, daterede leverancer under aktive opgaver, også datoer mere end 30 dage frem.
- Kundeopgavens almindelige redigering indeholder titel, beskrivelse, status og datoer. Evaluering har sin egen redigering og Gem-handling.
- Kundeopgaver kan fortsat oprettes direkte uden tilbud. Unødvendige oplysninger er fortsat valgfrie.

## Aftalegrundlag og honorarer

Et forslag til aftaleændring påvirker ikke gældende honorar. Først en aktiv accept anvender ændringen og registrerer tidspunkt, reference og før/efter. En reference kan være en kort beskrivelse af mail, møde eller mundtlig aftale; der kræves ikke et formelt dokument.

Accept uden reference er mulig, men vises udtrykkeligt som **Dokumentationsgrundlag ikke angivet**. Det sidestilles ikke visuelt med en angivet acceptreference.

Bindende honorarvilkår kan efter oprettelsen ikke ændres via almindelig opgaveredigering. Servicelaget afviser også sådanne direkte ændringer. Beløb, honorarmodel, timeloft, honorarloft, inkluderede timer og honorarnote behandles gennem aftaleændringer.

Et accepteret forslag anvendes kun én gang. Forslag fra et ældre aftalegrundlag afvises ved accept, hvis en anden ændring i mellemtiden er accepteret. Opret i så fald et nyt forslag ud fra den aktuelle aftale.

Det aktuelle honorar vises tydeligt. Det oprindelige kundeopgavesnapshot og tilbudskorrektionernes log bevares. Nye kundeopgaver fra tilbud får desuden et låst snapshot af tilbuddet ved oprettelsen. En tilbudskorrektion ændrer ikke automatisk kundeopgaven.

Danske beløbsfelter accepterer blandt andet `25000`, `25.000`, `25.000,00` og `25.000 kr.`. Tomt honorar og eksplicit `0 kr.` bevares som forskellige værdier. Timefelter accepterer ikke valutaendelser. Tvetydige talformater afvises fortsat.

## Migration og eksisterende data

Migration **006_agreement_acceptance** tilføjer status/tidspunkt, foreslåede vilkår og revisionsgrundlag til aftaleændringer samt tilbudssnapshot og bevaret gældende aftale til kundeopgaver. Tidligere migrationer er ikke omskrevet.

Eksisterende aftaleændringer får betegnelsen **Tidligere registreret – acceptstatus ikke registreret**. Deres hidtidige effekt og kundeopgavens aktuelle honorar bevares. En senere tilføjet historisk acceptreference anvender ikke honorarændringen igen. Tidligere referencer bevares ved supplering.

Manglende historisk tilbudssnapshot opfindes ikke. Det aktuelle tilbud kan allerede være korrigeret og kaldes derfor ikke automatisk det oprindeligt accepterede grundlag.

Opgradering er afprøvet på en isoleret version 5-database med eksisterende honorar og aftaleændring. Backup blev oprettet før migration; gendannelsestesten bevarede tabellernes rækketal fra før opgraderingen, og den opgraderede database bestod integritets-/foreign-key-kontrollen.

Ved rollback stoppes udviklingsappen, den nuværende database bevares separat, og en verificeret backup fra før migration 006 gendannes sammen med kodeversion `ea09e18`. Senere ændringer findes ikke i den gamle backup og skal bevares særskilt først.

## Automatiserede tests

Kommando: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.

**35 tests bestod.** Testene omfatter tidligere regressionstest og nye kontroller af:

- Deadline 24. oktober set fra 18. oktober, forfaldne datoer, i dag, dag 30/dag 31 og udaterede/afsluttede poster.
- Konsistente aktivitetsantal, sammenlægning af en gentaget deadline og bevarelse af selvstændig opfølgning.
- Klik på hver arbejdsoversigt og overensstemmelse mellem tal og viste poster.
- Direkte åbning af leverance, konkret møde/referat og en opfølgning, som standardfilteret ellers ville skjule.
- Honorarkæden tilbud 0, oprindeligt aftalt 2.700, tilbudskorrektion 20.000 og accepteret aftaleændring 25.000.
- Forslag uden effekt, accept med og uden reference, dobbeltaccept, forældet forslag, vilkårsændring uden nyt beløb og afvisning af direkte honorarændring.
- Bevarede oprindelige snapshots, gamle aftaleændringers økonomiske effekt og historisk dokumentation uden dobbelt anvendelse.
- Dansk beløbsformat, adskillelse fra timetal og visning af tidsstempler i dansk tidszone.
- Backup/gendannelse, migration, integritet, gamle arbejdsflows og fortsat driftsspærre.

Testkørslen fandt og rettede også en eksisterende kantfejl: meget hurtige accepterede tilbudskorrektioner kunne få samme tidsstempel og derfor blive afvist af beskyttelsestriggeren. En deterministisk test dækker nu denne situation.

## Browserkontrol

Udført på særskilt udviklingsdatabase med udelukkende syntetiske data, desktop **1440 × 1000** og mobil **390 × 844**.

Kontrolleret: synlig leverance den 24. oktober på dashboard, direkte åbning af leverancen, grupperet menu, områdevælger med tællere, aktuel honorarvisning, foreslået aftaleændring og registrering af accept med kort mundtlig reference. Mobilvisningen havde intet vandret sideoverflow. Browserloggen viste ingen fejl eller advarsler. Testserveren er stoppet efter kontrollen.

## Praktisk prøvevejledning

Brug kun udviklingsversionen via `Start Monitor Development.bat`.

1. **Dashboard:** Find den daterede leverance og vælg Åbn. Kontrollér, at den rigtige kundeopgave og leverance åbner med korrekt dato og prioritet. Redigér eventuelt en testdeadline og kontrollér den nye dato på forsiden.
2. **Arbejdsoversigter:** Klik eksempelvis Åbne leverancer eller Aktive kundeopgaver. Kontrollér, at posterne bag tallet vises, og åbn en af dem.
3. **Forretning:** Vælg forløb og skift mellem Pipeline, Tilbud, Kundeopgaver og Deadlines. Kontrollér, at Deadlines udelader leverede/annullerede og udaterede leverancer; alle leverancer findes fortsat under kundeopgaven.
4. **Aftaleændring:** Registrér et nyt testbeløb som Foreslået. Det aktuelle honorar skal stå uændret. Angiv en kort acceptreference og registrér kundens accept. Kontrollér nyt aktuelt honorar, oprindelig aftale og ændringshistorik. Kontrollér også en accept uden reference, hvor det manglende dokumentationsgrundlag skal fremgå.
5. **Opgave og evaluering:** Kontrollér, at Redigér kundeopgave ikke længere kan ændre honorar. Registrér timer/læring under Evaluering med egen Gem-handling. Prøv også en direkte kundeopgave uden tilbud med kun de nødvendige oplysninger.
6. **Menu:** Find Møder/Opfølgninger og Kontakter/Virksomheder via samlepunkterne. Observationer findes fortsat direkte; Signalindbakke, Kilder, Triggerregler og Briefing findes under Regulatorisk overvågning.

## Begrænsninger og drift

- Ældre direkte honorarrettelser uden registreret historik kan ikke rekonstrueres sikkert.
- Gamle møder får ikke automatisk status Forfalden eller Gennemført; der er ikke indført en ny mødestatusmodel.
- Enkelte engelske kalender-/tabelhjælpetekster stammer fra Streamlit. Tomme koblingslister vises nu med dansk tekst i stedet for et tomt valgfelt.
- Der er ikke udviklet automatisk overvågning, scraping, AI-funktioner, fakturering eller ny grafisk identitet. Ingen nye afhængigheder er tilføjet.
- Den aktive driftsdatabase er ikke brugt til SQLite-forbindelser eller migrationer. SHA-256 er uændret før/efter arbejdet: `B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.
- Driftsspærren er bevaret, og `main` er ikke ændret. Driftsoverførsel afventer særskilt godkendelse.

Etape 5 stopper efter implementering og test.
