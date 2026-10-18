# Etape 6.1b - kompakt brugerflade og navigation

## Ændringer

- Mindre topafstand på siderne. Den gentagne store programtitel, version og
  introduktion er fjernet fra hovedarbejdsområdet. Programnavnet står i sidepanelet;
  version, tilstand og dataplacering ligger under Om og tekniske oplysninger.
- UDVIKLINGSDATABASE står fortsat som synlig advarsel i sidepanelet i udviklingstilstand.
  Isoleret testtilstand vises som TESTDATABASE. En ekstra kompakt markering er
  tilføjet til hovedområdet, så tilstanden også fremgår, når sidepanelet er skjult.
- Mindre interne mellemrum i projektmodulet med bevaret afstand mellem sektioner.
- Opret projekt, Tilføj deltager, Opret nyt arbejdsspor og Tilknyt eksisterende
  forløb står i samme række som deres overskrift på brede skærme. Streamlits
  almindelige kolonner kan stables i smalle vinduer, så teksten ikke klemmes.
- Den relevante oprettelsesknap skjules, når oprettelsesformularen er åben.
  Formularens Opret/Gem og Annuller står i samme, afgrænsede handlingsrække.
  Annuller gemmer ikke indtastede ændringer. Formularnulstilling og kvitteringer
  fra 6.1a bevares.
- Returknappen er flyttet fra sidens top til umiddelbart under det konkrete
  forløbs overskrift. Den vises kun ved det forløb, der blev åbnet fra projektet.
  Eksisterende kontrol af projektrelationen og retur til samme projekt bevares.
- Tilknytningsvejledningen skelner mellem ingen deltagere, deltagere uden forløb,
  forløb tilknyttet dette projekt, forløb tilknyttet andre projekter og ledige forløb.
  Der oprettes ikke kommercielle forløb automatisk.

## Designaktiver og afvigelser

Ingen designmanual eller kompaslogo blev fundet i projektet eller den omgivende
arbejdsmappe. Den tidligere etape 4-rapport beskriver samme mangel. Der er derfor
ikke indsat eller konstrueret et logo og ikke gættet på manualens farvekoder.
Overskrifter genbruger projektets eksisterende mørkeblå tekstfarve `#243F50`
fra `.streamlit/config.toml`. Den præcise overensstemmelse med designmanualen
kan først bekræftes, når manual og logo er stillet til rådighed.

Ingen global redesignproces. Native Streamlit-komponenter anvendes; CSS er
begrænset til topafstand, overskriftsfarve, projektmellemrum og formularhandlinger.
Andre modulers egne formularer er ikke omlagt.

## Filer og teknik

- `app.py`: kompakt ramme, eksisterende farve, sidepanelinformation og sikkerhedsmarkeringer.
- `views/projects.py`: sektionsoverskrifter med handlinger, fælles handlingsrække,
  stabile formularpladser og situationsbestemt vejledning med læseforespørgsler.
- `views/business.py`: returknap ved forløbsoverskriften. Eksisterende forløbsvisning
  er udskilt til en renderfunktion, så projekt- og forløbsvisning har hver sin
  stabile plads og ikke efterlader formularrester ved skift.
- `tests/test_stage61b.py`: nye syntetiske UI-tests; tidligere tests er ikke svækket eller omskrevet.

## Testresultater

Kommando: `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`

**51 tests bestået.** Omfatter eksisterende sikkerhed, database, aftaler og
honorarbeskyttelse samt tidligere arbejdsflows og projektfunktioner. Nye tests
kontrollerer alle vejledningssituationer, sidepanelets testmarkering og
informationssektion, annullering af projekt/deltager/spor uden skrivning,
bevaret formularnulstilling, intet utilsigtet valg, ingen skrivning ved visning
og skjult returknap efter fjernelse af relationen. Navigation begge veje,
gemning, redigering og uændret forløb efter frakobling dækkes også af 6.1a-testene.

Browserkontrol i Edge på `127.0.0.1:8518` med særskilte syntetiske TEST-data:

- Desktopoversigt og sektionsknapper visuelt kontrolleret.
- Projektformular åbnet med tomme felter. Opret og Annuller målt med samme
  lodrette position. Annullering lukkede formularen.
- Projekt → forløb → samme projekt verificeret i browseren. Returknappen ligger
  direkte under det åbnede forløbs overskrift, ikke før filtrene.
- Ingen applikationsfejl observeret i browserloggen. Logfejl stammede fra
  browserens annonceblokeringsudvidelse.
- Begrænsning: anmodninger om 1366 x 900 og 768 x 1024 blev ikke pålideligt
  anvendt af browserværktøjet; den effektive bredde var fortsat omkring 1518 px.
  Senere skærmbilleder fejlede også i værktøjet. Derfor er forskellige bredder
  og formularernes smalle visning ikke visuelt færdigverificeret og skal
  efterprøves manuelt. Der påstås ingen fysisk iPad-test.

## Databeskyttelse og Git

Ingen ny migration; skemaversion 8 og alle eksisterende forretningsregler bevares.
Databasekode, services, runtime-konfiguration, startfiler og `.streamlit/config.toml`
er uændrede. Ingen kundedata er importeret eller anvendt til browsertesten.
Driftsdatabasen er ikke åbnet via SQLite eller ændret. SHA-256 før og efter:
`B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`.
Ingen driftsoverførsel eller ændring af driftsspærren. Ingen ny driftsbackup var
nødvendig, da drift og skema ikke berøres. UI-ændringer kan tilbageføres i Git.

Udviklingsgren: `codex/dashboard-3-foundation`, udgangspunkt `4271a81`.
`main` er uændret. Den midlertidige browsertest stoppes efter kontrollen;
brugerens eksisterende udviklingsserver og udviklingsregistreringer røres ikke.

## Praktisk prøvevejledning

1. Start eller genindlæs udviklingsversionen, og kontrollér UDVIKLINGSDATABASE.
   Brug fortsat kun syntetiske TEST-registreringer. Fold tekniske oplysninger ud
   i sidepanelet og kontrollér version og dataplacering.
2. Under Forretning → Projekter: kontrollér knapper ved sektionsoverskrifterne.
   Åbn Opret projekt, skriv en kladde og vælg Annuller. Ingen registrering må opstå.
3. Opret et TEST-projekt og kontrollér kvittering og tom formular ved genåbning.
   Gentag med deltager og arbejdsspor. Gem/Opret og Annuller skal hænge visuelt sammen.
4. Åbn et tilknyttet forløb. Returknappen skal stå ved forløbets overskrift og
   føre tilbage til præcis samme projekt. Kontrollér også frakobling uden forløbssletning.
5. Prøv Tilknyt eksisterende forløb på TEST-projekter uden deltagere, med en
   deltager uden forløb og med allerede tilknyttede forløb. Vejledningen skal passe.
6. Prøv almindeligt vindue, smallere vindue og eventuelt iPadbredde. Kontrollér
   læsbarhed, knapper, formularhandlinger og synlig databasemarkering, også med
   lukket sidepanel. Dette er det vigtigste tilbageværende manuelle kontrolpunkt.

Arbejdet stopper efter 6.1b. Ingen efterfølgende etape eller drift er frigivet.
