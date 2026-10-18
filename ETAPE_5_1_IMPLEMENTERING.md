# Etape 5.1 - daglige aktiviteter

Dato: 18. oktober 2026. Kun udviklingsgrenen `codex/dashboard-3-foundation`.

## Gennemfoert

- Selvstaendig opfoelgning kan oprettes fra Moeder med en direkte knap, uden et moede. Eksisterende `followups` genbruges.
- Moedeoprettelse kraever aktivt valg af aktoer og en titel; opfoelgning kraever titel. Enter indsender ikke oprettelses- eller redigeringsformularerne. Dette er ogsaa gennemfoert i virksomhedsprofilens manuelle moede- og opfoelgningsformularer.
- Datovaelgere med dansk format erstatter fritekstdatoer i disse formularer. Eksisterende ikke-fortolkelig datotekst bevares ved redigering; den kan erstattes ved at vaelge en dato.
- Moedeoversigten tilbyder direkte redigering af titel, dato, tid, sted, deltagere, resume, laering og naeste skridt. Dashboardets moedelink aabner samme redigering. Referattekst og tilknytninger bevares.
- Dashboardets opfoelgningslink aabner redigeringen udfoldet. Afslut opfoelgning saetter status Lukket. Dashboardet genberegnes fra databasen ved naeste visning.
- Sletning kraever afkrydsning. Moeder med tilknyttede dokumenter, briefinger eller observationer kan ikke slettes her. Forloebskoblinger fjernes sammen med et bekraeftet slettet moede. Samling af moeder bevarer nu ogsaa forloebskoblinger.
- Opfoelgningsoversigten medtager som standard ogsaa lav prioritet. Filtre kan stadig aendres.
- Forretningsomraader har tydeligere klikflader og valgt markering; taellere og grupperet venstremenu er bevaret. Ingen nye dashboardbokse.

## Test og databeskyttelse

` .\.venv\Scripts\python.exe -m unittest discover -s tests -v `: **36 tests bestaaet**.

Ny interaktiv AppTest afproever tom oprettelse, oprettelse/redigering af moede, selvstaendig opfoelgning uden ekstra moede, datovaelger, afslutning og fald i dashboardtaeller, fjernelse fra aktivitetslisten, bekraeftet sletning og beskyttelse af tilknyttet briefing. SQLite foreign_key_check er uden fejl efter testforloebet.

Eksisterende tests daekker alle navigationsvisninger, direkte dashboardmaal, honorarkaede/originalaftale, foreslaaede og accepterede aendringer, leverancefrister/status, dubletgruppering, backup/gendannelse, databaseisolation, AI-samtykke og driftsspaerre. Dette er maalrettet regressionstest, ikke en garanti for alle mulige historiske data og arbejdsgange.

Browserkontrol paa separat lokal testserver med syntetiske data: Enter uden moedeoprettelse, fejl ved tom titel, selvstaendig opfoelgningsformular, dansk datovaelger og skift til Tilbud med bevarede taellere. Visuel kontrol af formular ved 1440 x 1000 og 390 x 844; ingen vandret side-overloeb. Ingen registrerede browser-consolefejl. Oprettelse/redigering/afslutning/sletning er fuldt afproevet med AppTest, ikke alle gentaget manuelt i browser.

**Ingen skemaaendring eller ny migration.** Tests bruger nye isolerede databaser, ikke drift eller den eksisterende udviklingsdatabase. Ingen import, oprydning, overfoersel eller driftsstart. Ingen scraping eller eksterne API-kald. Testserveren stoppes efter kontrol; brugerens server paa 8514 beroeres ikke.

Driftsdatabasens SHA256 er uforandret foer/efter:
`B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.

## Praktisk afproevning

1. Brug kun udviklingsversionen. Under Moeder og opfoelgninger: vaelg Opret selvstaendig opfoelgning.
2. Vaelg testaktoeren, skriv Afventer dokumentation, vaelg 21-10-2026 og naeste handling Ryk kunden. Status Ny betyder aaben; Afventer er ogsaa en aaben status. Gem opfoelgning.
3. Gaa til Dashboard. Aabn opfoelgningen, ret dato/handling og gem. Vaelg Afslut opfoelgning og kontroller, at dashboardets aabne taeller falder, og aktiviteten forsvinder.
4. Under Moeder: forsoeg tom oprettelse og Enter. Intet moede maa oprettes. Vaelg aktoer og meningsfuld titel, gem og rediger via Aabn / rediger moede og referat.
5. Slet en fejlagtig testregistrering: foerst afkryds bekraeftelsen, saa Slet registrering. Moeder med tilknyttet materiale er beskyttet.
6. I Forretning: skift mellem Tilbud, Kundeopgaver og Deadlines, kontroller valgt markering, taellere, originalaftale og aendringshistorik.

## Anbefalet senere overgang til ren drift - ikke udfoert

1. Stop skrivende sessioner og tag tidsstemplede, integritetskontrollerede SQLite-backups af alle relevante databaser samt eventuelle tilknyttede filer. Bevar originalerne urorte. Eksisterende backupfunktion bruger SQLite-backup, ikke blot kopiering af en aaben databasefil.
2. Efter saerskilt godkendelse: opret en NY database paa ny sti med godkendt skemaversion. Den nuvaerende initialisering indlaeser seed-lister: brug derfor en kontrolleret seed-fri oprettelse til den rene drift. Undlad at omdoebe udviklingsdatabasen til drift og undlad at omgaa driftsspaerren.
3. Lav en ejer-godkendt overfoerselsliste: Nomeco, PharmaService og Glostrup Apotek; TMJ kun som konkret aktiv mulighed. Udvaelg tilhoerende kontakter, relevante moeder/referater, aftaler, opgaver, leverancer og opfoelgninger. Relation alene bliver ikke automatisk en salgsmulighed.
4. Overfoer kun godkendte poster med eksplicit gammel/ny ID-mapping og alle noedvendige relationer. TEST-poster, dubletter og foraeldede virksomheder udelades fra den nye database, men slettes ikke fra kilderne. Automatisk navnefilter er ikke tilstraekkelig udvaelgelse.
5. Sammenhold antal og stikproever med listen; valider honorarer, originalaftaler, historik, deadline/status, dokumenthenvisninger, foreign_key_check og integrity_check. Afproev dashboardlinks samt gendannelse til separat mappe. Ejer godkender foer skift af startkonfiguration.
6. Ved godkendt skift bevares gammel database, kodeversion og startkonfiguration til rollback. Tag backup foer opdateringer og dagligt ved brug; kopi til separat beskyttet placering. Bevar flere daterede versioner. Gendan kun til ny mappe, verificer foerst, og skift aldrig automatisk oven i en aktiv database.

Denne plan kraever en senere kontrolleret implementering; der er ikke bygget et overfoerselsvaerktoej nu.

## Senere dokumentregister og haendelser - kun vurdering

Et lille metadataregister kan senere have titel, kategori, dato, filreference/URL, valgfri aktoer og kundeopgave. Det skal pege paa eksisterende filer, ikke kopiere dem til nyt arkiv. Eksisterende tilbudsdokumentreference og uploaded_documents kan genbruges som henvisninger i visningen, men matcher ikke alene et samlet register. Adgang og flyttede filstier skal afklares foer implementering.

Eksisterende virksomhedstidslinje samler allerede moeder, briefinger, noter, observationer mv. Aftaleaendringer og tilbudsrettelser har bevaret historik. Followups viser status/updated_at, men gemmer ikke en fuld haendelseslog; leverancestatus er heller ikke i sig selv bevis paa afsendelse. En senere faelles visning boer genbruge disse registreringer; kun faktiske mangler som materiale efterspurgt/modtaget behoever eventuelt en lille eksplicit haendelsespost. Ingen nyt register eller historikmodul er implementeret.

## Begraensninger

- Aabne opfoelgninger benytter de eksisterende statusser Ny, Planlagt, I gang og Afventer; Lukket og Arkiveret er ikke aabne. Moeder har fortsat ikke et selvstaendigt statusfelt.
- Referattekst laeses fortsat i sin eksisterende visning; den nye formular redigerer moedets metadata/resume, ikke uploadfilen.
- Sletning er permanent efter bekraeftelse. Tilknyttet dokumentation skal afklares separat; systemet sletter den ikke med moedet.
- Gamle fritekstdatoer normaliseres ikke automatisk. Manuel udskiftning via datovaelger er mulig.
- Eksisterende udvidede funktioner uden for denne afgraensning er ikke omskrevet. Ingen driftsoverfoersel er frigivet.

Arbejdet stopper efter etape 5.1. Naeste etape og alle driftsaendringer afventer ejerens godkendelse.
