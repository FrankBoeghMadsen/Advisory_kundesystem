# Etape 6.1a - brugeroplevelse og navigation

## Afgrænsning

En afgrænset UI-forbedring oven på etape 6.1, commit `18123dd`, på
`codex/dashboard-3-foundation`. Ingen nye forretningsfunktioner, afhængigheder,
eksterne API-kald eller ændringer af projektmodellen. Drift er fortsat spærret.

## Gennemførte ændringer

- Projekter, deltagere og arbejdsspor vises som udgangspunkt i læsetilstand.
- Knapper åbner oprettelse eller redigering; kun én formular er åben ad gangen.
- Vellykket gemning lukker formularen, nulstiller næste oprettelse og viser en kort kvittering.
- Nyt projekt vises og vælges efter oprettelse. Valideringsfejl bevarer indtastningen.
- Nye deltagere og forløbstilknytninger starter uden valg. Gemning kræver aktivt valg.
- Flere samtidige projektroller bevares; rollemarkeringer har lys baggrund og mørk tekst.
- Arbejdsspor identificeres med titel, virksomhed eller Fælles spor og ID, også ved identiske titler.
- Deltagerfjernelse og sporsletning kræver fortsat bekræftelse. Kvitteringer beskriver resultatet.
- Forklarende tekst ved manglende tilgængelige forløb viser, hvordan eksisterende forløb kan tilknyttes.
- Frakobling giver kvittering og ændrer ikke selve det kommercielle forløb.
- Projektets Åbn-knap giver adgang til forløbet med en Tilbage til projekt-knap.
  Returforbindelsen valideres mod den eksisterende relation. Anden hovednavigation
  rydder retur- og redigeringskonteksten.

## Filer og teknisk løsning

- `views/projects.py`: kompakt oversigt, betingede formularer, formulargenerationer,
  eksplicitte valg, læsetilstand og kvitteringer.
- `ui/navigation.py`: valgfri projektkontekst i eksisterende navigation og sikker retur.
- `views/business.py`: returknap, når et forløb er åbnet fra et tilknyttet projekt.
- `app.py`: genbrug af eksisterende diskret multiselect-stil, afgrænset til projektmodulet.
- `tests/test_stage61.py`: tilpassede UI-interaktioner; eksisterende kerneassertioner bevares.
- `tests/test_stage61a.py`: isolerede syntetiske UI-regressionstests.

Der skrives ikke direkte til allerede oprettede widgetværdier. Pending navigation
anvendes før widgetoprettelse. En ny formulargeneration giver blanke oprettelsesfelter.

## Afvigelser og begrænsninger

Formularer åbnes med almindelige knapper og betinget rendering frem for en bogstavelig
Streamlit-expander. Det giver pålidelig lukning og nulstilling i Streamlit 1.41.1.
Annuller eller åbning af en anden formular kasserer et ikke-gemt udkast; der er ikke
indført kladdeopbevaring. Kvitteringer er kortvarige og forsvinder ved næste interaktion.
Et nyt arbejdsspor starter som Fælles spor, ikke med en bestemt virksomhed valgt.

## Tests

`./.venv/Scripts/python.exe -m unittest discover -s tests -q`

**49 tests bestået.** Dækker tidligere database-, sikkerheds-, aftale-, honorar-,
dashboard-, møde- og opfølgningsflows samt projektfunktionerne. Nye kontroller omfatter:

- Tom formular ved genåbning og lukkede formularer efter succes.
- Ingen utilsigtet virksomhed eller forløbstilknytning ved tomt valg.
- Kombinerede roller, korrekt målrettet redigering og forskellige labels ved samme sportitel.
- Oprettelses-, redigerings-, tilknytnings- og frakoblingskvitteringer.
- Projektvalg, tomtilstand og navigation til forløb og tilbage til samme projekt.
- Uændrede forløbsrækker efter frakobling og ingen databaseskrivning ved ren projektvisning.
- Foreign-key-check på isolerede testdatabaser.

Browserkontrol i Edge mod en særskilt syntetisk testdatabase på lokal port 8517:
læsetilstand og entydige sporlabels, projektoprettelse med kvittering og aktivt nyt
projekt, tom genåbnet formular, tomt forløbsvalg, eksplicit tilknytning med kvittering
og navigation til forløb og tilbage til samme projekt er kontrolleret. Ingen
applikationsfejl blev observeret i browserloggen; en fejl kom fra browserens
annonceblokeringsudvidelse, ikke fra appen. Smal visning blev visuelt
kontrolleret med viewportanmodning 390 x 844; browseren rapporterede effektiv bredde
434 px og samme dokumentbredde, uden vandret dokumentoverløb. Dette er ikke en
fysisk iPad-test. Øvrige detaljer bør efterprøves af brugeren efter vejledningen nedenfor.

## Database, migration og sikkerhed

Ingen migration i 6.1a; skemaversion 8 bevares. Databasekode, projektservice,
driftsspærre og begge startfiler er uændrede. Testdata er syntetiske TEST-registreringer;
ingen faktiske kundedata er importeret eller læst til browsertesten.

Driftsdatabasen `C:\Users\frank\FrankAdvisoryMonitorData\monitor.db` er ikke åbnet
via SQLite eller ændret. SHA-256 før og efter arbejdet:
`B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.
Ingen driftsbackup eller driftsmigration er kørt. Eksisterende backup- og
gendannelsesmekanismer er uændrede. Kodeændringerne kan tilbageføres i Git uden
databaseskemaændringer. Risikoen ved manglende global SQLite-FK-håndhævelse fra
6.1 består; den ændres ikke af denne UI-etape.

## Praktisk prøvevejledning

1. Start udviklingsversionen med `Start Monitor Development.bat`, ikke driftsstartfilen.
   Vælg Forretning → Projekter og brug udelukkende syntetiske testregistreringer.
2. Opret et TEST-projekt. Kontrollér kvittering, aktivt nyt projekt og lukket formular.
   Åbn Opret projekt igen; titel og formål skal være tomme. Vælg Annuller.
3. Tilføj deltager. Ingen virksomhed må være valgt. Vælg aktivt en TEST-virksomhed
   og flere roller. Gem, redigér rollerne og kontrollér oversigten og kvitteringerne.
4. Opret et fælles spor og et virksomhedsspor med samme titel. Kontrollér kontekst
   og ID. Redigér det ene; det andet må ikke ændres. Genåbn ny oprettelse og kontrollér nulstilling.
5. Åbn Tilknyt eksisterende forløb. Vælg aktivt et eksisterende TEST-forløb og gem.
   Vælg Åbn og derefter Tilbage til projekt. Det samme projekt skal vises uden åbent redigeringsfelt.
6. Frakobl forløbet. Kontrollér kvitteringen og at forløbet stadig findes under Forretning → Forløb.
7. Kontrollér i et mindre vindue, at oversigt, formularer og diskrete rollemarkeringer er læselige.

Arbejdet stopper efter 6.1a. Ingen driftsoverførsel eller funktioner fra 6.2–6.6 er godkendt eller udført.
