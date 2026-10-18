# Ren drift og de første kunder - beslutningsgrundlag

Ingen af nedenstående overførsler, oprydninger eller driftsstarter er udført. Ingen faktiske kundeposter er oprettet eller ændret som led i analysen. Kundernes aktuelle forhold skal verificeres af ejeren, ikke udledes af tidligere illustrative scenarier.

## Kontrolleret overgang

1. **Fastfrys og sikkerhedskopiér:** Efter særskilt godkendelse standses skrivende sessioner. Tag dateret SQLite-backup af hver relevant kilde samt backup af eventuelle lokale bilag. Registrer kodeversion, skemaversion og kontrolsummer. Bevar originaler og backup urørte og adgangsbeskyttede; ingen kilde skal overskrives eller ryddes op.
2. **Ny database på ny sti:** Byg en tom kandidatdatabase med den godkendte skemaversion i et separat stagingmiljø. Den nuværende `init_db()` indlæser seed-lister, når tabeller er tomme. Ren drift kræver derfor en senere eksplicit, seed-fri initialisering; man må ikke blot bruge almindelig førstegangsopstart eller udviklingsdatabasen. Driftsspærren må ikke ophæves før accept.
3. **Ejerens tilladelsesliste:** Godkend præcist hvilke virksomheder og relaterede poster der skal med. Start med Nomeco, PharmaService og Glostrup Apotek; TMJ kun med bekræftet konkret relation/aktivt lead/planlagt indsats. Overvågningsvirksomheder kommer ikke automatisk med. Testdata udelukkes efter indholds- og oprindelseskontrol, ikke alene ved et TEST-navnefilter.
4. **Selektiv overførsel:** Overfør godkendte stamdata, kontakter, forløb, tilbud, kundeopgaver, leverancer, relevante møder/referater, noter, beslutninger og åbne/lukkede opfølgninger. Vurder briefinger og øvrig historik enkeltvis. Kopiér ikke hele overvågningsdelen. Brug en dokumenteret gammel/ny ID-mapping, transaktioner og foreign-key-kontrol. Bevar oprindelige aftalesnapshots og rettelses-/acceptlog uden at genberegne honorarer eller omskrive historien. Kilde-ID og oprindelse dokumenteres også ved indlejrede historiske referencer.
5. **Valider før drift:** Sammenlign overførselslisten med antal pr. tabel og kunde. Kør integrity_check, foreign_key_check og relevante automatiske tests. Kontroller økonomiske aftaleoplysninger, originalaftale, accepterede ændringer, datoer, status, afslutningsnoter, mødekoblinger og bilagsreferencer manuelt. Afgørende uoverensstemmelser stopper overførslen.
6. **Hold miljøerne adskilt:** Udvikling beholder sin særskilte startfil, tydelige tilstandsmarkering og `.dev-data`; kandidaten testes på egen sti. Først efter ejerens godkendelse skiftes den fastlagte driftskonfiguration kontrolleret til den nye database. Godkendt kodeversion fastholdes; ingen automatisk driftsoverførsel fra udviklingsgrenen. Lokal binding til 127.0.0.1 og AI-samtykke bevares.
7. **Backup og tilbageførsel:** Tag backup før skift og før hver senere opdatering samt dagligt ved anvendelse. Opbevar flere daterede versioner og en separat beskyttet kopi. Gendannelsestest foretages til en ny mappe med integritetskontrol og stikprøvevis åbning, aldrig oven i den aktive database. Ved rollback standses skrivning, den aktuelle database bevares, og tidligere kode/startkonfiguration/database genaktiveres samlet efter kontrol. Nye registreringer siden skiftet skal afstemmes, ikke tabes stiltiende.

## Manuel acceptliste før start

- Kun ejer-godkendte kunder/leads er synlige i det aktive overblik; ingen seed- eller testkunder.
- Hver kontakt tilhører rette kunde; telefon/mail og eventuelle dubletter er gennemgået.
- Hvert forløb er et konkret behov, ikke blot en generel relation. Flere behov hos samme kunde er adskilte forløb.
- Tilbudsversioner, originalaftale, gældende honorar og ændringshistorik stemmer med kildematerialet.
- Kommende møder, bindende leverancefrister, forventede beslutningsdatoer og opfølgningsfrister er skilt korrekt ad.
- Åbne opfølgninger vises én gang; afsluttede kan findes med resultat og kendt afslutningsdato.
- Dashboardets Åbn-links fører til rigtige møder, leverancer og opfølgninger.
- Filer kan findes på de angivne stier; kandidatens database indeholder ikke uønskede kopier eller fortrolige testudtræk.
- Backup er gendannet og verificeret separat; rollback og ansvar for godkendelse er aftalt.

## Første kundegennemgang med eksisterende felter

Brug samme korte gennemgang for Nomeco, PharmaService, Glostrup Apotek og TMJ. Bekræft først hvilke registreringer der allerede er korrekte. Opret kun mangler efter godkendelse, uden dobbeltregistrering.

| Behov | Eksisterende funktion | Arbejdsgang |
| --- | --- | --- |
| Kontaktpersoner | Kontakter med kunde, rolle, telefon, mail; primær kontakt på forløb | Genbrug personen og knyt vedkommende til rette kunde/forløb. |
| Konkret behov | Forretningsforløb, behovsbeskrivelse, rådgivningsområde, status | Ét forløb pr. behov. En relation alene kræver ikke et forløb. |
| Tilbud og aftalegrundlag | Versionerede tilbud med omfang, leverancer, forudsætninger, honorar og dokumentreference | Alternative/reviderede tilbud bliver i samme forløb. Accepteret tilbud og ændringer behandles med eksisterende beskyttelse. |
| Kundeopgave og honorar | Kundeopgave direkte eller fra accepteret tilbud; honorarmodel, beløb, note og originale snapshots | Direkte oprettelse er fortsat mulig, også historisk. Dokumentér grundlaget; foreslåede ændringer må ikke ændre gældende honorar. |
| Møder og beslutninger | Møder med referat, resume, næste skridt; møde-forløbskoblinger, noter | Genbrug samme møde i flere relevante forløb. Gem acceptreference ved aftaleændring. |
| Modtaget kundemateriale | Noter, møder/referat og eksisterende fritekstfelter; tilbud har dokumentreference | Indtil dokumentregister findes kan en relevant note angive dokumenttitel, dato og filsti. Det er ikke et struktureret materialeregister; almindeligt materiale skal ikke registreres som et fiktivt møde. |
| Egne leverancer | Leverancer under kundeopgave: titel, beskrivelse, status, frist og afslutning | Én konkret leverance pr. meningsfuldt resultat. Filreference kan midlertidigt stå i beskrivelsen; intet nyt uploadarkiv. |
| Deadlines og opfølgninger | Leverancefrist, opfølgningsdato, prioritet, person og næste handling | Knyt opfølgning til forløb og eventuelt leverance, når relevant. Bevar uden kobling, når den gælder relationen generelt. |
| Afslutning og evaluering | Kundeopgavens afslutning, resultat/læring, faktisk tid, genanvendelse og fremtidigt samarbejde; opfølgningens resultat/dato | Afslut frem for at slette. Opret kun et nyt fremtidigt forløb ved et konkret nyt behov. |

For hver af de fire kunder besluttes særskilt: aktiv kunde eller lead, hvilke konkrete behov der findes, korrekt aftalegrundlag, åbne handlinger og hvilke historiske oplysninger der er nødvendige. Analysen fastslår ikke nye faktiske opgaver eller honorarer.

## Dokumentregister senere - ikke implementeret

Anbefalet enkel model: dokument-ID, titel, dokumentdato, dokumenttype, filsti/URL, kunde-ID og valgfrit kundeopgave-ID samt en kort note. Dokumenttypen er et begrænset valgsæt, fx Kundemateriale, Tilbud, Aftale, Notat, Præsentation, Værktøj og Korrespondance. Filen forbliver i sin nuværende mappe; databasen gemmer kun metadata og henvisning. Flyttede filer og adgangsrettigheder skal håndteres, og en filsti er ikke et universelt iPad-link.

Eksisterende `proposals.document_reference` og referatuploads genbruges i overblikket frem for at skabe dubletter. De dækker ikke hele behovet. En senere lille tabel kan supplere disse, uden at gamle uploads flyttes eller kopieres. Kundens materiale må ikke automatisk sendes til AI.

Virksomhedstidslinjen og aftale-/tilbudslog kan allerede understøtte dele af sags- og relationshukommelsen. Afsluttede opfølgninger har nu resultat og tidspunkt. Det er stadig ikke en fuld hændelseslog, og en status Leveret beviser ikke i sig selv, at materialet faktisk er sendt. Praktiske erfaringer i drift bør afgøre, om eksplicitte begivenheder som Materiale modtaget og Leverance fremsendt senere er nødvendige. Ingen ny dokument- eller hændelsesfunktion er bygget i etape 5.2.

## Næste beslutning

Ejeren godkender først etape 5.2 og derefter særskilt datagrundlag, selektionsliste, seed-fri etablering og kandidatkontrol. Indtil da er planen alene dokumentation og eksisterende driftsmiljø uændret.
