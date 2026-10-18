# Etape 6.0 - teknisk gap-analyse og løsningsdesign

## 1. Ledelsesopsummering

**Anbefaling: Model 2, et valgfrit projektniveau med små faglige arbejdsspor, genbrug af eksisterende forretningsobjekter og særskilt honorarfordeling.** Ingen ny workflowmotor, projektstyringsplatform, bogføring eller dokumentarkiv.

Den eksisterende kæde er virksomhed → forretningsforløb → tilbud/kundeopgave → leverance. Den fungerer til én kunde, men virksomhedstilknytningen anvendes både til navigation, sammenhæng og kommerciel identifikation. Den kan ikke alene udtrykke Megros som koordinator/aftalepart, Nomeco/TMJ som faglige deltagere og PharmaService som selvstændigt betalingsforpligtet deltager.

Tre afgørende skel skal indføres i et senere, godkendt design: **fagligt spor er ikke en salgsmulighed; deltagelse er ikke betalingspligt; leveret/faktureret er ikke accepteret/betalt.** Fem faglige trin må være mærkater, ikke obligatoriske porte.

Et projekt skal være valgfrit. Almindelige rådgivningsopgaver skal fortsat kunne oprettes direkte hos én kunde uden projekt, tilbud, betalingsplan eller ekstra registreringer. Den eksisterende honorarbeskyttelse skal bevares og udvides afgrænset til accepterede fordelinger, ikke omgås.

Dette er en statisk analyse af commit **`0c980d0`** på **`codex/dashboard-3-foundation`**, ikke en implementering. Kun denne rapport er tilføjet. Ingen appopstart, databaseforbindelse, migration, seeding, import, nye tests eller testkørsel er udført. Ingen kundedata er indlæst. Casen nedenfor er alene brugerens kravbeskrivelse.

## 2. Kilder og eksisterende løsning

### 2.1 Kodegrundlag

Henvisningerne gælder ovenstående commit. D-, S-, U- og T-numrene bruges i resten af rapporten.

| Ref. | Kilde og anvendelse |
| --- | --- |
| D1 | [db.py:97](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/db.py:97): kontakter; møder fra linje 161; opfølgninger fra 234. |
| D2 | [db.py:431](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/db.py:431): migration 4, forløb, tilbud, kundeopgaver, leverancer og koblinger. |
| D3 | [db.py:548](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/db.py:548): migration 5–7, snapshots, tilbudskorrektioner, aftaleændringer og afslutning af opfølgninger. |
| D4 | [db.py:262](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/db.py:262): forbindelser, integritetskontrol, backup og gendannelsestest; initialisering fra linje 661. |
| S1 | [business_service.py:17](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/services/business_service.py:17): aktiv tilbudskonvertering, feltliste og honorarbeskyttelse fra 95, ændringsaccept fra 171, relationsregler fra 260. |
| S2 | [activity_service.py:10](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/services/activity_service.py:10): dashboardets virksomhedsafledning, statusfiltre, dato/prioritet og dubletgruppering. |
| S3 | [followup_service.py:5](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/services/followup_service.py:5): kun forløb hos samme virksomhed. |
| S4 | [advisory_service.py:97](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/services/advisory_service.py:97): virksomhedstidslinje; briefingkontekst fra 185. |
| U1 | [business.py:76](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/views/business.py:76): åbne/lukkede opfølgninger, forløbseditor, mødekoblinger, tilbud, opgaver, leverancer og evaluering. |
| U2 | [tasks.py:23](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/views/tasks.py:23): selvstændige opfølgninger, valgfri forløbskobling, afslutning og resultat. |
| U3 | [contacts.py:12](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/views/contacts.py:12): kontaktregister; redigering flytter én kontakt mellem virksomheder. |
| U4 | [navigation.py:3](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/ui/navigation.py:3): grupperet menu og direkte åbning; [activity_editor.py:14](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/ui/activity_editor.py:14): kontrolleret sletning og møderedigering. |
| U5 | [app_config.py:8](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/app_config.py:8): aktørtyper og statusmodeller. |
| T1 | [test_business_workflows.py:1](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/tests/test_business_workflows.py:1): eksisterende tests, herunder afvisning af tværgående virksomhedskoblinger. |
| T2 | [test_stage52.py:20](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/tests/test_stage52.py:20): afslutningshistorik, migration, genstartsspærre og interaktive opfølgningsforløb. |
| R1 | [runtime_config.py:39](C:/Users/frank/Documents/Codex/2026-05-30/kan-du-finde-vores-l-ngerevarende/frank_advisory_monitor_v2_4/runtime_config.py:39): eksplicit tilstand og adskillelse af drifts-/udviklingsstier. |

### 2.2 Objekter og kardinalitet

| Objekt | Nuværende struktur og betydning | Begrænsning |
| --- | --- | --- |
| Virksomheder | `companies` repræsenterer også brancheforeninger, myndigheder og person/relation via aktørtype. Navn er unikt. | Ingen struktureret virksomhed-virksomhed-relation, projektmedlemskab eller rolle pr. projekt. Aktørtypen Person / relation er ikke en fælles personidentitet. |
| Kontakter | `contacts.company_id` er valgfri; én række har ét navn, én virksomhed og rolle/kontaktoplysninger. | Samme person i to organisationer kræver to rækker uden fælles identitet. Rolle er fritekst; ingen gyldighedshistorik. Flytning af rækken kan ændre konteksten for allerede tilknyttede forløb. |
| Forløb | `commercial_tracks.company_id NOT NULL`; én primær kontakt; titel, konkret behov, område, beslutningsdato og afslutningsårsag. Flere forløb pr. virksomhed. | Ét forløb har præcis én virksomhedsreference. Ingen deltagerliste eller overordnet projekt. Det er et kommercielt behov, ikke et neutralt fagligt spor. |
| Tilbud | Mange `proposals` pr. forløb, version, omfang, forudsætninger, honorarmodel, beløb, dokumentreference og status. `UNIQUE(track_id,version)`. | Virksomhed og aftalepart afledes af forløbet. Ingen modtager-/betalerfordeling eller betalingsmilepæle. Versioner er søskende, ikke en eksplicit revisionskæde; alternativer og revisioner skelnes primært gennem indhold. |
| Kundeopgaver | Mange `engagements` pr. forløb; tilbud valgfrit. Titel, beskrivelse, aftalt honorar, datoer, status, evaluering og fremtidigt samarbejde. | Kunde afledes gennem forløbet. Et accepteret tilbud kan højst bruges af én opgave via et partielt unikt indeks. Flere forskellige tilbud/direkte opgaver kan eksistere i samme forløb. Ingen betalerrelation. |
| Aftalehistorik | Oprindeligt snapshot, accepteret tilbudssnapshot, aftalerevision og ændringsrækker. Foreslåede og accepterede ændringer adskilles. | Honorar er én værdi/én model pr. opgave. Historikken indeholder ikke betalingsfordeling. Korrektion af tilbud ændrer ikke automatisk den oprettede opgaves aftale. |
| Leverancer | Mange `deliverables` pr. kundeopgave med titel, beskrivelse, dato, prioritet, status, afslutning og ansvarlig-note. | Én opgave pr. leverance. Virksomheden arves gennem opgaven/forløbet. Ingen særskilt modtagervirksomhed, fagligt spor, metodetrin eller afhængigheder. Leveret betyder ikke kundeaccept/effekt. |
| Møder | Ét `company_id NOT NULL`; deltagere er tekst. `meeting_tracks` er mange-til-mange. | Service og UI tillader kun forløb hos samme virksomhed som mødet. Fælles workshop kan omtale alle i tekst, men har kun én struktureret virksomhedskontekst. Ingen kontakt-ID'er for deltagere. |
| Opfølgninger | Virksomhed, forløb og leverance er valgfrie; højst én af hver. Næste handling og person er tekst. Etape 5.2 tilføjede resultat og seneste afslutningstidspunkt. | Forløb skal tilhøre samme virksomhed. Ingen projektkontekst eller struktureret initiativ hos rådgiver/kunde/ekstern/begivenhed. Flytning til andet forløb rydder gammel leverancekobling. |
| Noter/observationer | Virksomhedsnoter, møderesume, observationsdata med verifikations-/fortrolighedsfelter, evaluering på opgaven. | Kan midlertidigt beskrive beslutninger og effekt, men ingen samlet projektbeslutning eller konsekvent effektklassifikation. Observationsverifikation bør ikke forveksles med dokumenteret rådgivningseffekt. |

**Konklusion:** En kontakt-/mødetekst med flere virksomhedsnavne løser ikke de strukturelle huller. Ingen eksisterende tabel binder virksomheder sammen som projektparter. Systemet har heller ingen faktura-, betalings-, projekt- eller afhængighedstabel. Dette er konstateret i kode, ikke ved læsning af den aktive database.

### 2.3 Hvor håndhæves reglerne?

| Regel | Database | Applikationslogik | Brugerflade / konsekvens |
| --- | --- | --- | --- |
| Et forløb har én virksomhed | Én ikke-null `company_id`-kolonne. | Ingen generel projektregel. | UI vælger én aktør og låser valget ved normal redigering af eksisterende forløb. |
| Referentiel integritet | FK er deklareret. | `connect()` aktiverer ikke `PRAGMA foreign_keys=ON`; der er ikke fundet anden aktivering i kode. Initialisering/backup kontrollerer særskilt med `foreign_key_check`. | Deklarerede FK må derfor ikke regnes som garanteret håndhævede på normale forbindelser. Runtime-PRAGMA er ikke målt i denne analyse. En efterkontrol er ikke løbende FK-håndhævelse. |
| Tilbudsversion/konvertering | Unik version pr. forløb; accepteret tilbud unikt blandt opgaver med tilbudsreference. | Konvertering kræver eksisterende tilbud og afviser genbrug; foretages i transaktion. | Aktiv brugerhandling, ikke automatisk opgave ved statusvalg. |
| Gyldige statusser, datoer og beløb | Ingen relevante status-`CHECK`, typedato eller generel ikke-negativ-beløbsbegrænsning. `NOT NULL` for titel forhindrer ikke tom tekst. | Generisk gemmeservice kontrollerer titel, udvalgte numeriske felter og feltliste; andre funktioner har egne regler. | Valglister, talparser og datovælgere giver yderligere kontrol. Ikke alle regler er en databasegaranti eller fælles på tværs af skriveveje. |
| Samme virksomhed ved møde/opfølgning/leverancekobling | Ingen tværkolonnebegrænsning mellem de relevante virksomhedsreferencer. | `set_track_meetings`, `set_track_followups`, `set_deliverable_followups` og `validate_track` kontrollerer samme virksomhed. | U1/U2 filtrerer kandidater til samme virksomhed. Det er en reel servicebarriere, ikke kun et filter. |
| Primær kontakt tilhører rette virksomhed | FK refererer kun kontaktens ID, ikke kontaktens virksomhed. | Generisk gemmeservice håndhæver ikke denne tværrelation. | Kontaktlisten filtreres på virksomheden. Kontaktflytning gennem U3 kontrollerer ikke efterfølgende påvirkning af allerede valgte primære kontakter. |
| Accepteret tilbud beskyttes | Trigger kræver en logpost med passende nyt tidspunkt ved UPDATE. Ikke generel immutabilitet; omfatter ikke DELETE. | Begrundet korrektion; accepteret status må ikke ophæves og tilbuddet må ikke flyttes gennem korrektionsvejen. | Accepteret indhold vises skrivebeskyttet med særskilt korrektion. Trigger kontrollerer loggens eksistens/tidspunkt, ikke selv alle ændringers semantik. |
| Oprindelig aftale/gældende honorar | Snapshots er tekst/JSON; ingen tilsvarende uforanderlighedstrigger på kundeopgaven. | Feltliste udelukker direkte snapshotredigering. Ændring af honorarvilkår afvises ved almindelig gemning. Accept af ændring kontrollerer revision og anvender vilkår atomisk én gang. | Original/gældende aftale og foreslåede/accepterede ændringer vises adskilt. Rå SQL er ikke tilsvarende beskyttet. |
| Afslutning af opfølgning | Migration 7 registrerer tidspunkt ved overgang til Lukket og ved ny lukket post uden dato. | Dashboard filtrerer Lukket/Arkiveret fra. | Resultat er valgfrit. Gamle lukkede poster kan mangle dato. Genåbning bevarer seneste afslutning/resultat; det er ikke en fuld hændelseslog. |
| Sletning/historik | Ingen generel soft-delete/auditgaranti. | Mødesletning beskytter tilknyttet dokumentation og AI-opfølgning; eksplicit slettefunktion kræver bekræftelse. | Permanent sletning af opfølgning er fortsat mulig efter bekræftelse. Kontaktsletning har en anden, ældre arbejdsgang. |

Generisk gemning tillader bl.a. relationelle ID-felter uden en fuld tværkontrol af accepteret tilbud, opgave og forløb. Det er en grund til at samle **nye projektskrivninger** i små, transaktionelle servicefunktioner med målrettede tests, ikke til at omskrive alt nu. En global aktivering af FK uden audit af gamle sletteveje er en særskilt ændring, som kræver godkendelse og regressionstest.

### 2.4 Statusser, fremdrift og UI

Statusser fra U5: forløb Åben/Afventer/Pauset/Lukket; tilbud Kladde/Klar til afsendelse/Sendt/Afventer/Accepteret/Afvist/Udløbet/Trukket tilbage; opgave Planlagt/I gang/Afventer/Afsluttet/Annulleret; leverance Ikke startet/I gang/Afventer/Leveret/Annulleret; opfølgning Ny/Planlagt/I gang/Afventer/Lukket/Arkiveret. Der er **ingen fælles tilstandsmaskine**, der tvinger alle poster gennem en bestemt rækkefølge. Ikke-lineær behandling er delvist mulig allerede; det manglende er spor, fælles kontekst og afhængigheder.

Forretning viser ét valgt forløb og områderne Pipeline, Tilbud, Kundeopgaver, Deadlines og Afsluttet. Møder/opfølgninger og kontakter/virksomheder er grupperet i menuen. Dashboardet viser daterede aktiviteter frem til 30 dage samt overskredne frister, særskilte udaterede aktiviteter og arbejdsoversigter. Forventet beslutning er markeret ikke-bindende. Aktive kunder afledes fra aktive kundeopgaver og deres forløbsvirksomhed; deltagere og betalere tælles ikke selvstændigt. Tidslinje og briefingkontekst filtrerer på én virksomhed. De er ikke projektoversigter og skal ikke udvides med alle deltageres fortrolige materiale uden eksplicit kontekstvalg.

## 3. Megros som funktionel stresstest

### 3.1 Faktagrænser

**Supplerende kravpræcisering ved godkendelsen af etape 6.1:** Bestyrelsen godkendte det oprindelige Megros-tilbud på 85.000 kr. ekskl. moms; Henrik meddelte godkendelsen den 3. september 2026. Den senere udvidelse og honorarfordeling skal dokumenteres særskilt. Dette er alene opdateret kravgrundlag, ikke registrering af faktiske kundedata eller en implementeret økonomimodel. Nedenstående oprindelige forbehold om den første accept er dermed afklaret; det må ikke overføres til forbeholdet om den senere udvidelse.

Ingen af disse scenarieposter er registreret. Beløb er ekskl. moms i DKK. Den oprindelige godkendelse på 85.000 kr. er nu oplyst, meddelt af Henrik den 3. september 2026. Øvrige ikke oplyste datoer, fakturanumre, betalingsfrister og acceptreferencer må ikke opfindes. Den senere udvidelse og honorarfordeling skal dokumenteres særskilt; den oprindelige accept er ikke samtidig dokumentation for denne ændring.

| Element | Korrekt fremstilling i den anbefalede model |
| --- | --- |
| Samlet projekt | Megros – strategisk regulatorisk dialog; aktivt, med udestående fælles arbejde. Ikke procentfærdigt udledt af fem metodetrin. |
| Roller | Megros: koordinator, aftalepart og betaler 80.000. PharmaService: deltager og selvstændigt betalingsforpligtet 40.000. Nomeco/TMJ: deltagere, ikke selvstændige fakturamodtagere for interne Megros-andele. Andre kontraktroller må ikke udledes alene af betalingspligt. |
| Oprindeligt tilbud | Bevar 85.000 som original tilbudsversion. Registrér ikke en fiktiv accept eller overskrivning til 120.000. |
| Senere aftale | Samlet økonomisk ramme 120.000; accepteret fordeling 80.000 + 40.000. Fordelingen er en opdeling af de 120.000, ikke ekstra omsætning oveni. |
| Betalingsmilepæle | Megros: 40.000 a conto og 40.000 ved afslutning. PharmaService: 20.000 a conto og 20.000 ved afslutning. Ved afslutning er en betingelse, ikke en opdigtet kalenderfrist. |
| PharmaService-faktura | Én oplyst udstedt acontoregning 20.000; faktisk betalingsstatus og betalt beløb ukendt. Ikke markeret betalt, ubetalt eller forfalden uden yderligere grundlag. |
| Megros-faktura | Ingen udstedelse er oplyst. Vis Ingen faktura registreret/udstedelse ikke oplyst, ikke Betalt og ikke en opfundet faktura. Fravær af registrering beviser heller ikke, at faktisk fakturering er nul. |
| Samlet faktureringsvisning | Kendt registreret faktureret: 20.000, med tydelig markering af datagrundlagets fuldstændighed. Vis ikke 100.000 som dokumenteret endnu-ikke-faktureret eller 20.000 som dokumenteret ubetalt. |

### 3.2 Faglige spor og næste handling

| Spor | Leverance/faglig tilstand | Næste initiativ og begrænsning |
| --- | --- | --- |
| Nomeco | Omfattende regulatorisk analyse leveret. | Kundereaktion og eventuelle videre handlinger udestår; initiativ Kunde. Leveret er ikke dokumenteret rådgivningseffekt eller kundens godkendelse. |
| PharmaService | Konsolideret forståelsesgrundlag og juridisk analyse leveret. | Opfølgende evaluering planlagt; dato og aktuel initiativhaver afklares, ikke gættes. |
| TMJ | Mindre fremskredent ifølge scenariet. | Konkrete færdige aktiviteter/leverancer og næste handling er ikke oplyst; ikke automatisk Ikke startet. |
| Fælles spor | Workshop, tværgående syntese og endelige anbefalinger udestår. | Planlægges med eksplicitte forudsætninger. Fælles workshop behøver ikke ligge før allerede leverede analyser. |

FORSTÅ, UDFORSK, ANALYSÉR, ANBEFAL og BESLUT bruges som valgfri faglige mærkater. Afhængighed angives konkret, fx at en fælles syntese afventer input fra flere spor. Det er et design-eksempel, ikke en antagelse om casens faktisk aftalte rækkefølge. Hele projektet lukkes ikke automatisk, fordi ét spor har leveret.

Nomecos mulige myndighedsmøde/mødeforberedelse, PharmaServices mulige leverandørgodkendelsesindsats og senere implementering bliver **nye muligheder** med valgfri oprindelsesreference til projektet. De får hverken accepteret status, gældende honorar eller projektets leverancer overført automatisk. Det skal være tydeligt, hvad der er indeholdt, foreslået tillægsarbejde og særskilt nyt behov.

## 4. Gap-matrix

P1 = nødvendig før Megros kan håndteres pålideligt; P2 = lille støttefunktion efter kernen; P3 = udskydes, medmindre praksis viser behov.

| Behov | Eksisterende støtte | Faktisk mangel | Anbefalet håndtering | Prioritet |
| --- | --- | --- | --- | --- |
| Flere virksomheder i ét projekt | Flere forløb, ingen fælles overbygning | Intet fælles projekt/roller | Valgfrit projekt og projektparter med flere samtidige roller | P1 |
| Faglige virksomhedsspor | Leverancer/opfølgninger | Spor må ellers foregives som salg/opgaver | Små arbejdsspor med valgfri virksomhed og ét fælles spor | P1 |
| Ikke-lineær metode | Frie statusvalg | Ingen metodekontekst | Valgfrit metodemærkat på leverancer; ingen porte | P1 |
| Fælles leverancer/møder | Én virksomheds forløb; møde-M:N inden for virksomheden | Service afviser tværgående kontekst | Projektkontekst og eksplicitte mødevirksomheder, ikke globale undtagelser | P1 |
| Person i flere organisationer | Separate kontaktposter | Ingen fælles personidentitet/rollehistorik | Valgfri personidentitet bag eksisterende kontakt-ID'er; senere styret sammenkobling | P1 for flerrollebehov |
| Initiativ hos kunde/ekstern | Persontekst og Afventer | Ansvarstype og begivenhed mangler | Valgfri initiativtype + kort afventer-note på opfølgning | P1 |
| Afhængigheder | Fritekst | Ikke struktureret på tværs af spor | Enkel leverance-til-leverance-forudsætning uden auto-status | P2; tekstlig støtte først |
| Flere betalingspligtige | Ét opgavehonorar | Ingen beløbsfordeling/acceptversion | Versioneret fordeling under én samlet aftaleramme | P1 |
| A conto/slutbetaling | Honorarnote | Ingen beløb/betingelse pr. betaler | Betalingsmilepæle på forpligtelser, ikke faglige deadlines | P1 |
| Faktureret kontra betalt | Ingen struktureret støtte | Ukendt/ikke betalt blandes let | Manuelle fakturareferencer og eksplicit ukendt betalingsstatus | P1 |
| Aftaleændringer | Snapshots og accepteret ændringsservice | Fordeling kan ikke følge revision | Atomisk accept af beløb/fordeling, bevaret historik | P1 |
| Nye opgavemuligheder | Eksisterende forløb/tilbud | Ingen relation til oprindelsesprojekt | Projektkoblet mulighed, tydeligt uden for aftalt omfang | P1 |
| Beslutninger/kundereaktion/effekt | Noter, observationer, evaluering | Ingen projektkontekst eller entydig evidenstype | Valgfri projektnote med type og evidensniveau | P2 |
| Historiske opfølgninger | Etape 5.2 | Ingen tværgående projektfiltrering | Genbrug samme poster; tilføj kontekst, bevar dato/resultat | P1 |
| Dokumentregister | Tilbudsreference og referatupload | Ingen generel projekt-/opgavereference | Bevar separat senere etape; brug korte henvisninger nu | P3 |
| Fortrolighed i projekt | Fortrolighed/samtykke | Deltagelse er ikke ret til alle bilag | Visning/adgang og eventuelt eksport skal afgrænses; ingen automatisk AI-samling | P1 |

## 5. Sammenligning af løsningsmodeller

| Kriterium | 1. Få felter/relationer på eksisterende forløb | 2. Valgfrit projektniveau med små spor | 3. Fuld projekt-/arbejdsgangsmotor |
| --- | --- | --- | --- |
| Dækning | Deltagerkobling og fritekst kan give midlertidigt overblik, men løser ikke fælles aftale, betalerfordeling og særskilte faglige spor samtidigt. | Dækker hovedbehov med genbrug af eksisterende poster og smalle tillæg. | Kan dække alt, men kræver generalisering langt ud over casen. |
| Model | Fx forløbsdeltagere + nye betalingsfelter. Forløbet får både salgs-, projekt- og sporbetydning. | Projekt, parter, spor samt uafhængige aftale-/betalingsrelationer; tilbud/opgaver forbliver kommercielle. | Egen aktivitetstype, generisk graf, stadier, afhængighedsmotor og evt. mange-til-mange på alt. |
| UI/byrde | Færre nye skærme, men brugeren skal vælge kunstig ankervirksomhed og forklare undtagelser i noter. | Ét valgfrit samlet overblik. Et simpelt kundejob kræver intet nyt. | Mange indstillinger og registreringer, også for små opgaver. |
| Eksisterende funktioner | Betydningen af forløb og virksomhed svækkes; risiko for skjulte undtagelser i alle filtre. | Eksisterende en-kunde-forløb bevares. Projekterede visninger tilføjes eksplicit. | Flere gamle workflows erstattes eller får parallelle objekter. |
| Dubletter/inkonsistens | Stor risiko for kopierede fælles møder og opgaver samt dobbelt honorar. | Begrænset ved fælles ID'er, én honorarkilde og validerede kontekster. | Kan håndteres, men flere synkroniserings- og overgangsregler. |
| Migration | Ser lille ud, men ændrer semantik i gamle felter; ikke reelt lav risiko. | Overvejende additive tabeller/nullable referencer; ingen automatisk ændring af gamle kundedata. Personidentitet kræver særskilt kontrol. | Omfattende konvertering og større rollbackbehov. |
| Test/vedligehold | Få startændringer, mange specialtilfælde senere. | Målrettede relation-, beløbs-, historik- og UI-tests pr. tillæg. | Stor kombinatorisk testflade og løbende workflowvedligeholdelse. |

**Model 2 anbefales**, men ikke som et løfte om, at to ekstra felter løser hele behovet. Kernemodellen er tre små strukturer; personidentitet og betaling er særskilte, afgrænsede tillæg. Model 3 fravælges: der er ikke behov for ressourceplanlægning, Gantt, automatisk kritisk vej, timeføring pr. aktivitet, obligatorisk stage-gate eller en universel relationsgraf.

## 6. Anbefalet minimumsdatamodel

Alle navne er designforslag, ikke SQL eller eksisterende tabeller. Nye referencer er som udgangspunkt valgfrie på gamle objekter. Obligatoriske felter begrænses til det nødvendige for den registrering, brugeren aktivt vælger at oprette.

### 6.1 Projekt, parter og spor

| Struktur | Minimumsfelter og relationer |
| --- | --- |
| `projects` | ID, titel, status (Planlagt/Aktivt/Afventer/Afsluttet/Annulleret), kort formål, valgfrit `primary_engagement_id`, oprettet/ændret. Projektet er en organisatorisk ramme, ikke en juridisk person. |
| `project_company_roles` | `project_id`, `company_id`, `role`; sammensat unik nøgle på alle tre. Roller: koordinator, aftalepart, betaler, deltager, begunstiget. Flere roller pr. virksomhed; UI viser én virksomhed med rollevalg, ikke fem dublerede virksomheder. Ingen generel koncern-/ejerrelation udledes. |
| `project_workstreams` | ID, projekt, titel, valgfri virksomhed, enkel status og valgfri næste-skridt-note. Virksomhed NULL betegner fælles spor. Flere spor hos samme virksomhed er mulige. Ingen tilbuds-/honorarfelter på et fagligt spor. |
| Eksisterende `commercial_tracks` | Valgfrit `project_id` + tilknytningsform: Indeholdt grundforløb eller Særskilt mulighed. Behold én `company_id`; det er stadig den kommercielle hovedrelation, ikke alle deltagere/betalere. En projektkobling ændrer ikke status eller skaber en aftale. |
| Eksisterende leverancer | Valgfrit `workstream_id` og metodemærkat. Én eksisterende kundeopgave forbliver kontrakt-/økonomisk anker; modtagerspor kan være Nomeco under en Megros-forankret opgave. UI skal vise forskellen på aftalekontekst og faglig modtager. |
| Eksisterende opfølgninger | Valgfrit `project_id`, `workstream_id`, `action_owner_type` og `waiting_for_note`; eksisterende virksomhed, person, dato, status, resultat og afslutning genbruges. Initiativtype: Rådgiver/Kunde/Ekstern/Afventer dato eller begivenhed/Ikke angivet. En event-baseret handling kræver ikke opdigtet frist. |

Projektets `primary_engagement_id` angiver den økonomiske hovedramme for denne minimumsmodel, ikke at alle deltagere hæfter over for hinanden. Opret projekt uden anker, derefter forløb/opgave, og tilknyt ankeret; ingen ikke-null-cyklus kræves. Ankerets forløb skal tilhøre projektet. Særskilte muligheder indgår aldrig i hovedrammens honorarsum.

For Megros anbefales én samlet opgaveramme på 120.000 med betalerforpligtelser 80.000/40.000, **hvis ejeren godkender, at denne samlede opgave repræsenterer projektets faglige og økonomiske ramme**. Det må ikke vises som Megros' egen betalingspligt på 120.000. Alle økonomiske virksomhedsvisninger skal i projektkontekst vise rolle og egen betalingsforpligtelse særskilt. Hvis materialet reelt kræver flere uafhængige aftaler/opgaver med adskilt scope, skal denne beslutning genbesøges før økonomietapen: brug da flere ikke-overlappende opgaver med projekttotal afledt af dem, ikke en ekstra samlet 120.000-opgave oveni. Det spørgsmål afgøres ikke ved at opfinde aftaleforhold i casen.

### 6.2 Møder og personer uden dubletter

- Tilføj valgfrit `meetings.project_id` og eventuelt ét primært `workstream_id`. Fælles møde har projektkontekst uden at tilhøre et bestemt virksomhedsspor.
- `meeting_companies(meeting_id,company_id)` giver eksplicit flere virksomhedskontekster. Bevar gammel `meetings.company_id` som primær/historisk registreringskontekst. Visning er union af primær og eksplicitte relationer, deduplikeret på møde-ID. Projektmedlemskab alene er ikke bevis for mødedeltagelse.
- Fælles møder kan vises som fælles projektmøder under spor uden at kopiere dem eller foregive, at alle har deltaget. Eksisterende `meeting_tracks` og samme-virksomhedsregler fortsætter for almindelige møder. En ny projektservice kan tillade eksplicit delt projektkontekst, men må ikke blot fjerne alle eksisterende virksomhedschecks.
- `persons(id,display_name)` og valgfrit `contacts.person_id` samler personidentitet. En eksisterende kontakt bliver en organisationsrelation med sin egen rolle, mail/telefon og historiske ID. To organisationsroller er to relationer, men én person. Ingen automatisk sammenlægning ud fra navn/mail. Gamle kontakt-ID'er og referencer bevares.
- Personens navn redigeres ét sted ved fælles identitet; gamle kontakt-navne bevares som historisk/fallbacktekst, ikke endnu en uafhængig master. Kontaktspecifikke oplysninger forbliver hos organisationsrelationen.
- `meeting_contacts(meeting_id,contact_id)` kan tilføjes, når strukturerede deltagere vælges. UI grupperer samme person og viser relevante tilhørsforhold; gammel deltagertekst bevares uden automatisk fortolkning. Refereret organisationsrelation må ikke blot flyttes til ny virksomhed; opret en ny relation, og markér eventuelt den gamle inaktiv med gyldighedsdato. Ingen automatisk omskrivning af gamle møder.

Opfølgning hos Nomeco i Megros-projektet behøver ikke sætte `commercial_track_id` til Megros-forløbet, hvilket i dag afvises. Brug i stedet projekt-/sporkontekst og behold Nomeco som virksomhedsreference; projektoversigten finder samme opfølgning dér. Et eventuelt eksisterende kommercielt forløb skal stadig passe til virksomheden. Så kan gamle regler bevares, mens tværgående overblik opnås gennem det nye niveau.

### 6.3 Aftale, forpligtelser og fakturastatus

| Struktur | Felter og regler |
| --- | --- |
| `fee_allocation_sets` | ID, kundeopgave-ID, aftalerevision, valgfri ændrings-ID, status Foreslået/Accepteret/Historisk uafklaret, acceptreference/tidspunkt og historisk total-snapshot. Én gældende accepteret fordeling pr. aftalerevision. Snapshot er historik, ikke endnu en redigerbar gældende totalsum. |
| `fee_obligations` | Fordelingssæt, betalende virksomhed, beløb, valgfri konkret aftalepart og kort grundlagsreference. Betalende virksomhed skal have betalerrolle i projektet; deltagerrolle giver ikke automatisk betalingspligt. En reference må være mail/møde/mundtlig aftale; ingen tvungen upload. |
| `payment_milestones` | Forpligtelse, betegnelse, beløb, betingelse og valgfri dato. Fx A conto eller Ved afslutning. Gem beløb; procent kan vises afledt, så to redigerbare sandheder undgås. Sum af milepæle skal stemme med den accepterede forpligtelse. |
| `invoice_records` | Milepæl, udstedt beløb, valgfrit nummer/link og udstedelsesdato, betalingsstatus Ukendt/Ikke betalt/Delvist betalt/Betalt, valgfrit kendt betalt beløb/dato og note. Fakturamodtager afledes af forpligtelsen; ikke af leverancens modtagerspor. |

Fakturaer udstedes stadig uden for systemet. Registreringen henviser blot til dokumenterede forhold; ingen momsberegning, fakturanummerserie, kreditorkartotek, rykkere, bankafstemning eller bogføring. Manglende betalingsoplysning er NULL/Ukendt, ikke nul eller Ikke betalt. Beløb gemmes helst som heltalsøre i nye tabeller med ikke-negativ kontrol og DKK som eksplicit valuta; nuværende beløbsfelter konverteres ikke generelt i denne etape.

En faktura kan dække en del af en milepæl; flere referencer er mulige. Udstedt beløb må ikke ændres stiltiende for at matche en ny aftale. Afvigelser kræver særskilt forklaring og kontrolleret rettelse, ikke sletning af historik. Kreditnotaer/tilbagebetalinger ligger uden for minimumsmodellen og kræver senere godkendt håndtering, hvis behovet opstår.

Ved accepteret aftaleændring skal samlet honorar, accepteret fordeling og milepæle hænge sammen i **én transaktion**. Genbrug den eksisterende revisionskontrol/acceptfunktion via en afgrænset serviceudvidelse; almindelig gemning af fordelingsrækker må ikke ændre honoraret. Foreslået fordeling har ingen effekt før accept. Accepterede sæt bevares og ændres kun gennem ny revision. Hvis en eksisterende ændring foretages uden ny fordeling, markeres fordelingen uafstemt og må ikke vises som gældende afklaret. Udstedte fakturareferencer forbliver på deres historiske grundlag og tælles én gang ved sum på tværs af revisioner.

**Én sandhed om honoraret:** gældende opgavehonorar = 120.000; accepterede betalerforpligtelser skal summere til 120.000. 80.000 + 40.000 vises som fordeling, ikke som yderligere opgavehonorarer. Betalingsmilepæle summeres aldrig som ny omsætning. For en almindelig enkeltkundeopgave uden fordelingsbehov genbruges det eksisterende honorarfelt uden krav om disse tabeller.

### 6.4 Beslutninger, værdi og afhængigheder

En lille valgfri `project_notes`-struktur kan supplere eksisterende noter: projekt, valgfrit spor/virksomhed, dato, kort tekst, type (Forventningsafstemning/Beslutning/Kundereaktion/Mulig effekt/Dokumenteret effekt) og valgfri kildehenvisning. Dokumenteret effekt kræver et bevidst evidensvalg og en kort reference; almindelig note kræver ikke en bevispakke. Notér, om noget er forventet, observeret eller dokumenteret. Kundens positive reaktion er ikke automatisk dokumenteret regulatorisk eller økonomisk effekt. Ingen obligatorisk effektmåling ved hver leverance.

Afhængigheder kan i første projektvisning stå i næste handling/forudsætningsnote. Hvis struktureret støtte godkendes, er minimum `deliverable_dependencies(deliverable_id,prerequisite_id)` med unik nøgle, ingen selvreference og servicekontrol for samme projekt og cykler. En milepæl kan være en almindelig eksisterende leverance uden dokumentfil. Vis Afventer forudsætning som afledt information, men ændr ikke brugerens gemte status og blokér ikke arbejde i andre spor. Ingen automatisk fremrykning af metodetrin eller lukkestatus.

### 6.5 Invarianter før en senere implementering kan accepteres

1. Projektrolle kan være flertydig, virksomheden er ikke dubleret; medlemskab er ikke lig med betalingspligt eller adgang til alle bilag.
2. Spor, hovedopgave og kontekst skal høre til samme projekt. Virksomhedsoplysninger må ikke modsige valgte organisations-/sporrelationer. Nullable projektfelter ændrer ikke almindelige en-kunde-regler.
3. Ét møde, én opfølgning og én leverance har ét kanonisk ID; flere visninger og relationer må ikke give flere aktiviteter eller omsætningstællinger.
4. Summen af accepterede forpligtelser matcher gældende honorar; milepæle matcher forpligtelser. Forslag og særskilte muligheder tæller ikke med.
5. Fakturabeløb, kendt betaling og ukendt betaling er forskellige felter/tilstande. Ingen automatisk betaling ved levering eller afslutning.
6. Gammel aftale, tilbudsversion, afslutningsnote og deltagertekst bevares. Person-/kontaktkobling må ikke omskrive historiske organisationsroller.
7. Fagligt metodetrin, arbejdsstatus, initiativhaver, leveret, accepteret og betalt er selvstændige begreber. Ingen af dem bruges som stedfortræder for de andre.

## 7. Brugeroplevelse

Ingen grafisk implementering foreslås nu. Bevar den eksisterende menu; lad Forretning tilbyde en enkel visning af projekter ved siden af almindelige forløb.

```text
Megros - strategisk regulatorisk dialog                  Aktivt
Megros: koordinator/aftalepart/betaler | øvrige deltagere og roller

Næste handlinger
Dato/begivenhed | handling | spor | initiativ | Åbn

Faglige spor
Nomeco         Analyse leveret; kundereaktion udestår         Åbn
PharmaService  Grundlag og analyse leveret; evaluering planlagt Åbn
TMJ            Fremdrift/næste handling afklares               Åbn
Fælles         Workshop, syntese og anbefalinger udestår       Åbn

Aftale og betaling
Oprindeligt tilbud 85.000 | senere aftale 120.000 | historik
Betaler        Aftalt forpligtelse | milepæle | fakturareference | betaling
Megros         80.000               40/40       ikke oplyst       ukendt
PharmaService  40.000               20/20       20.000 udstedt     ukendt

Beslutninger og kundereaktioner | særskilte muligheder | henvisninger
```

Projektets overordnede status vælges enkelt; den viser ikke en vilkårlig procent baseret på fem faser. Åbn fører til den eksisterende redigering af objektet. Afsluttede handlinger kan foldes ud. En fælles aktivitet vises én gang med relevante spor, ikke som én kopi pr. virksomhed. Virksomhedsprofilen viser egne kommercielle forløb samt Deltager i projekter; deltagelse får ikke automatisk kunden til at se faktureret ud.

**Almindelig en-kundeopgave:** vælg kunde → eksisterende/nyt konkret forløb → Opret kundeopgave direkte → titel, eventuelt honorar og relevante leverancer/opfølgninger → gem. Projekt er tomt, ingen roller, spor eller fordelingsplan skal udfyldes. Ved senere behov kan opgaven eksplicit knyttes til et projekt; ingen automatisk kopiering eller konvertering af gamle poster.

## 8. Risici, migration og teststrategi

### 8.1 Største risici

Den største forretningsrisiko er et korrekt regnestykke med forkert betydning: Megros kan fejlagtigt fremstå betalingspligtig for 120.000, eller 120.000 + 80.000 + 40.000 kan blive talt som 240.000. Den største relationsrisiko er at ophæve samme-virksomhedsregler globalt og dermed tillade vilkårlige krydsreferencer. Den største historikrisiko er at samle kontaktposter eller revidere accepterede beløb ved overskrivning. Disse håndteres gennem eksplicit rolle/kontekst, én honorarkilde, kanoniske ID'er og versioneret accept.

Den svage garanti omkring FK-håndhævelse er en eksisterende teknisk observation, ikke ændret her. Senere nye tabeller skal have faktiske PK/UNIQUE/FK/CHECK-regler, og skrivende forbindelsers håndhævelse skal verificeres. Global ændring af forbindelser kræver særskilt konsekvensanalyse af gamle data og sletteveje; ingen stiltiende aktivering som del af en projektskærm.

### 8.2 Senere kontrolleret migration

Først efter godkendelse: fastlæg kode-/skemaversion, tag verificeret backup og opret en isoleret kopi. Tilføj tabeller og nullable referencer trinvist; ingen automatisk oprettelse af projekter fra alle virksomheder, ingen seeding af Megros-casen og ingen automatisk personsammenlægning. Nye projektvisninger skal være valgfrie, indtil de er valideret. Indfør ikke både gammel og ny redigerbar master for samme opgave eller honorar.

Gem før/efter-optællinger, ID-/feltkontrol, originale aftalesnapshots og integritetsresultater. Afprøv gammel en-kundeopgave, etape 5.2 og nye projektcases på kopien. Stop ved uafstemte relationer/beløb. Gendan til en ny mappe og verificér, før en tilbagerulning godkendes; behold gammel kode/startkonfiguration og database samlet. Additive tabeller gør ikke gammel kode sikker på en ny database: tilbagefør også data, og afstem eventuelle nye registreringer. Driftsovergang og seed-fri ren database er fortsat en separat, ikke-godkendt handling.

### 8.3 Testdesign - ikke kørt i denne etape

- Bevar eksisterende tests for afvisning af vilkårlige tværgående koblinger. Tilføj positive tests kun for eksplicit, gyldig projektkontekst. Tværprojektkobling og primær kontakt fra forkert organisation afvises.
- Enkeltkundeopgave uden projekt kræver ingen nye felter og bevarer navigation, honorarhistorik, opfølgningens afslutningsdato/resultat og slettebeskyttelse.
- Samme person i Megros og en virksomhed vises som én person med to roller; gamle kontakt-/mødereferencer bevares ved ændring af en relation. Identiske navne alene må ikke fusioneres.
- Fælles møde vises i projekt og eksplicitte virksomhedskontekster med ét ID. Dashboard og projektoptælling deduplikeres også ved flere roller/joins.
- Faglig stresstest: Nomeco-analyse kan være Leveret før fælles workshop; det lukker ikke TMJ-sporet eller projektet. Eventuelle cirkulære/selvrefererende afhængigheder afvises uden auto-statusændringer.
- Økonomisk stresstest: oprindeligt tilbud 85.000 forbliver uændret; original accept gættes ikke. Senere accepteret ramme 120.000 fordeles 80.000/40.000; forslag har nul effekt. 79.000/40.000 afvises som uafstemt. Samtidig/stale accept afvises, og transaktionsfejl ruller både honorar og fordeling tilbage.
- Milepæle er 40.000/40.000 og 20.000/20.000. PharmaService-faktura 20.000 er udstedt med betaling Ukendt. Ingen Megros-faktura oprettes automatisk. Levering/afslutning må ikke ændre faktura-/betalingsstatus.
- Nye muligheder påvirker ikke grundhonorar eller accepteret omfang. Projektsummer må ikke inkludere både hovedrammen, dens fordelinger og mulige fremtidige opgaver.
- Test backup/gendannelse, faktiske FK/unikhedsregler og ingen utilsigtet skrivning ved visning. Browserkontrol af enkeltkunde og projekt på desktop/iPad-bredde samt tydelig initiativ-/betalerrolle. Ingen eksterne API'er kræves.

Den tidligere aflevering oplyste 41 beståede tests. Her er testkoden alene læst; **ingen nyt grønt testresultat eller runtime-verifikation påstås**. Ingen browser er startet, da denne etape ikke ændrer UI og appopstart kan initialisere data.

## 9. Små implementeringsetaper efter særskilt godkendelse

Hver række er et forslag, ikke en igangsat opgave eller samlet tilladelse til alle etaper.

| Etape | Afgrænsning | Acceptkriterium |
| --- | --- | --- |
| 6.1 Projektkerne | Projekter, parter/roller, små spor og valgfri kobling af eksisterende forløb. Kun nødvendige læse-/redigeringsvisninger. | Syntetisk Megros-projekt med fire virksomheder og fælles spor; intet nyt tilbud/opgave oprettes automatisk. Enkel en-kundeopgave virker uden projekt. Backup og rollback af den additive migration dokumenteres. |
| 6.2 Faglig kontekst | Projekt-/sporkontekst på leverancer, møder og opfølgninger, initiativtype og projektoversigt. | Parallel fremdrift, ét fælles møde uden dubletter, korrekte næste handlinger og uændret 5.2-historik. Gamle samme-virksomhedsregler er stadig aktive uden for projektkontekst. |
| 6.3 Personrelationer | Personidentitet bag kontakter og eksplicitte mødedeltagere. Ingen automatisk fusion. | Én person med to organisationsroller, bevarede gamle ID'er, ingen historikomskrivning eller flyttet primær kontakt uden kontrol. |
| 6.4 Aftale og betalerfordeling | Efter afklaring af samlet/selvstændigt aftalegrundlag: accepterede fordelinger og betalingsmilepæle, atomisk sammenhæng med aftalerevisioner. | 120.000 tælles én gang; 80.000/40.000 og respektive 50/50-planer er konsistente; forslag ændrer intet. Originalhistorik bevares. Ingen fakturering udføres. |
| 6.5 Manuel faktura-/betalingsreference | Lille registrering af eksternt udstedte fakturaer og kendt/ukendt betaling, ingen bank-/økonomiintegration. | 20.000 udstedt til PharmaService med ukendt betaling; ingen automatisk Megros-faktura. Kendte registreringer og manglende oplysninger vises forskelligt. |
| 6.6 Små støttefunktioner | Kun efter praktisk behov: beslutnings-/effektnoter og strukturerede afhængigheder. | Frivillige korte noter skelner forventet/observeret/dokumenteret; ingen sekventielle porte eller obligatorisk ekstraarbejde. |

6.1 kan leveres og afprøves isoleret, men må ikke præsenteres som fuld understøttelse af den økonomiske Megros-case. Dokumentregister, AI-udvidelser, hosting og driftsdataoverførsel er ikke med i disse forslag.

## 10. Åbne beslutninger og næste trin

1. Godkendes projekt som valgfri overbygning og fagligt arbejdsspor som noget andet end kommercielt forløb? Det er den afgørende modelbeslutning.
2. Skal Megros-casen repræsenteres af én samlet faglig/økonomisk kundeopgave med selvstændige betalerforpligtelser, eller kræver de faktiske aftaler to uafhængige kundeopgaver med forskelligt scope? Før økonomietapen skal aftalepart, betalingspligt og grundlag verificeres uden at antage solidarisk hæftelse.
3. Den oprindelige accept af 85.000 kr. er afklaret ved ejerens præcisering. Hvad er de særskilte acceptreferencer/datoer for udvidelse og fordeling? Ukendt historik skal fremgå som ukendt, ikke udfyldes automatisk.
4. Er seneste afslutningsdato/resultat tilstrækkelig for opfølgninger, eller ønskes senere historik over genåbninger? Anbefaling nu: bevar 5.2 og undlad en ny auditmotor.
5. Er én primær faglig sammenhæng pr. leverance nok? Anbefaling: én leverance i et fælles spor ved flere modtagere, ikke kopier eller generisk mange-til-mange på alt.
6. Godkendes en fælles personidentitet med organisationsspecifikke kontaktoplysninger og eksplicit sammenkobling? Der bør ikke indføres automatisk navne-/mailbaseret fusion.
7. Er manuel registrering af fakturareference, kendt betalt beløb og status nok? Anbefaling: ja; betaling starter som Ukendt, og faktiske betalingsfrister registreres kun, når de kendes.
8. Hvilke konkrete faglige afhængigheder og initiativhavere gælder? Ingen generel femtrinsrækkefølge eller konkrete deadlines er antaget. Strukturerede afhængigheder kan vente.
9. Hvilket materiale må vises samlet i et projekt, og hvad er virksomhedsspecifikt? Intern projektvisning er ikke en godkendelse til deling med andre deltagere eller AI.

**Næste udviklingstrin anbefales at være særskilt godkendelse af model 2 og etape 6.1 alene.** Afklar samtidig den økonomiske repræsentation i spørgsmål 2–3, men implementér den først i en selvstændigt godkendt etape. Begynd på isolerede syntetiske data; gennemfør ingen driftsoverførsel, og ophæv ingen eksisterende forretningsregel uden eksplicit godkendelse.

## 11. Afleveringskontrol

Kun denne Markdown-rapport er oprettet. Applikationskode, tests, konfiguration og databaseskema er uændrede; ingen database er åbnet gennem applikationen. Ingen migration, seed, testkørsel eller faktisk kundeimport. Den kendte driftsdatabase er alene læst som fil til SHA256-kontrol; indhold er ikke undersøgt. Kontrolsum før og efter er ens: `B6F439D74EEB7FD4645F7756451F4704BEC3F675E7AA4CCC95E37773CCE34DF5`. Alle 17 kildehenvisningers filstier og linjenumre er kontrolleret; Git viser kun denne nye rapport, ingen ændringer i eksisterende filer.

Rapporten beskriver et senere mål og acceptkriterier, ikke funktioner der allerede findes. Arbejdet stopper efter rapporten og afventer eksplicit godkendelse.

**Afsluttende anbefaling: Godkend model 2 og afgræns næste udvikling til etape 6.1, projektkernen på isolerede testdata. Afklar den økonomiske repræsentation før en senere, særskilt godkendt økonomietape. Ingen implementering eller driftshandling påbegyndes uden din godkendelse.**
