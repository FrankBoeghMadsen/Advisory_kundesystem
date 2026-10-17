import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def ai_briefing_text(company_name, context_text, allow_external=False):
    """AI briefing via OpenAI with local fallback."""
    if not allow_external:
        return f"""# Ekstern AI er ikke anvendt

Af hensyn til fortrolighed sendes oplysninger kun til OpenAI, når du aktivt godkender det for den konkrete generering.

{local_briefing_text(company_name, context_text)}
"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

            prompt = f"""
Du er senior strategisk rådgiver for Frank Bøgh Madsen Advisory.

Lav en konkret, kortfattet og handlingsorienteret mødeforberedelse på dansk til et kommende møde med aktøren: {company_name}.

Formålet er ikke at skrive en lang analyse, men at give Frank et praktisk brief, som kan bruges lige før og under mødet.

Brug kun oplysninger fra konteksten nedenfor.
Du må gerne:
- sammenholde oplysninger på tværs af møder, noter, signaler, observationer, sager og åbne opfølgninger
- identificere mønstre og uafklarede forhold
- foreslå konkrete spørgsmål
- pege på forhold der bør verificeres
- pege på mulige regulatoriske, strategiske eller kommercielle muligheder

Du må IKKE opfinde fakta. Hvis grundlaget er tyndt, så sig det tydeligt og foreslå hvad Frank bør afklare i mødet.

Skriv i et professionelt, direkte sprog. Brug korte afsnit og punktform. Prioritér det vigtigste først.

Struktur:
# 1. Kort situationsbillede
# 2. Hvad Frank bør opnå med mødet
# 3. Åbne opfølgninger og aftaler
# 4. Spørgsmål Frank bør stille
# 5. Forhold der bør verificeres
# 6. Mulig rådgivnings- eller kommerciel vinkel
# 7. Anbefalet mødetaktik
# 8. Efter mødet: næste handlinger

Kontekst:
{context_text[:18000]}
"""

            text = ""
            if hasattr(client, "responses"):
                response = client.responses.create(
                    model=model,
                    input=prompt,
                    temperature=0.2
                )

                if hasattr(response, "output_text"):
                    text = response.output_text

                if not text:
                    try:
                        text = response.output[0].content[0].text
                    except Exception:
                        text = ""
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Du er en præcis dansk advisory-assistent. Brug kun den givne kontekst, og markér tydeligt når noget bør afklares."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                try:
                    text = response.choices[0].message.content or ""
                except Exception:
                    text = ""

            if text and text.strip():
                return text

            return "AI-modellen returnerede ikke noget indhold."

        except Exception as e:
            return f"""# AI-fejl

Der opstod en fejl ved AI-briefing.

Fejl:
{str(e)}

Kontroller:
- at OPENAI_API_KEY er sat korrekt
- at internet virker
- at OpenAI-kontoen har API-adgang
- at modellen findes

Lokal fallback:

{local_briefing_text(company_name, context_text)}
"""

    return f"""# AI ikke aktiveret

OPENAI_API_KEY er ikke sat på computeren.

Systemet bruger derfor lokal briefing-skabelon.

For at aktivere AI:
1. Opret OpenAI API-nøgle
2. Kør i PowerShell eller CMD:

setx OPENAI_API_KEY "din_nøgle"

3. Genstart programmet

{local_briefing_text(company_name, context_text)}
"""


def local_briefing_text(company_name, context_text):
    return f"""# Mødebriefing: {company_name}

## 1. Kort situationsbillede
- Gennemgå seneste møder, observationer, signaler og historiske sager.
- Fokusér især på oplysninger markeret som ikke verificeret eller bør verificeres.

## 2. Hvad Frank bør opnå med mødet
- Afklare om relationen, behovet eller kundeforløbet har ændret sig siden sidst.
- Få bekræftet konkrete næste skridt, timing og relevante beslutningstagere.

## 3. Åbne opfølgninger og aftaler
- Hvad blev aftalt sidst?
- Er der åbne opfølgningspunkter eller frister?
- Er der personer eller relationer, der bør aktiveres?

## 4. Spørgsmål Frank bør stille
- Hvilke kvalitetsmæssige eller regulatoriske forhold fylder mest lige nu?
- Hvad er ændret siden sidst i organisation, QA/RA/GMP eller ledelse?
- Er der konkrete projekter eller frister hvor ekstern sparring kan skabe værdi?

## 5. Forhold der bør verificeres
- Hvilke oplysninger er fortsat antagelser eller baseret på ældre møder?
- Er der nye risici, deadlines eller beslutninger, som bør dokumenteres?

## 6. Mulig rådgivnings- eller kommerciel vinkel
- Strategisk sparring om myndighedsdialog
- Gennemgang af regulatoriske problemstillinger
- Forberedelse til inspektioner eller opfølgning
- Overblik over risici og næste skridt

## 7. Anbefalet mødetaktik
- Start med relationen og seneste udvikling.
- Gå derefter til konkrete åbne punkter og behov.
- Slut med tydelige næste skridt og aftalt opfølgning.

## 8. Efter mødet: næste handlinger
- Gem referat eller hovedpointer på profilen.
- Opret opfølgning/lead med dato, person og næste handling.
- Opdater briefing eller noter, hvis der kom ny strategisk viden.
"""


def ai_meeting_followup_text(
    company_name, meeting_title, meeting_text, context_text, allow_external=False
):
    """AI follow-up from meeting minutes with local fallback."""
    if not allow_external:
        return f"""# Ekstern AI er ikke anvendt

Af hensyn til fortrolighed sendes referatet kun til OpenAI, når du aktivt godkender det for den konkrete generering.

{local_meeting_followup_text(company_name, meeting_title)}
"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

            prompt = f"""
Du er senior strategisk rådgiver for Frank Bøgh Madsen Advisory.

Lav en konkret opfølgningsanalyse på dansk efter mødet/referatet:
Virksomhed: {company_name}
Møde: {meeting_title}

Brug kun oplysninger fra referatet og konteksten nedenfor.
Du må ikke opfinde fakta.

Struktur:
# Kort møderesume
# Aftalte næste skridt
# Åbne spørgsmål
# Mulige rådgivningsmuligheder
# Regulatoriske eller strategiske opmærksomhedspunkter
# Relationer/personer at følge op med
# Foreslået konkret opfølgning

Referat:
{meeting_text[:14000]}

Kontekst:
{context_text[:6000]}
"""

            text = ""
            if hasattr(client, "responses"):
                response = client.responses.create(
                    model=model,
                    input=prompt,
                    temperature=0.2,
                )
                if hasattr(response, "output_text"):
                    text = response.output_text
                if not text:
                    try:
                        text = response.output[0].content[0].text
                    except Exception:
                        text = ""
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Du er en præcis dansk advisory-assistent. Brug kun den givne kontekst.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
                try:
                    text = response.choices[0].message.content or ""
                except Exception:
                    text = ""

            if text and text.strip():
                return text
            return "AI-modellen returnerede ikke noget indhold."

        except Exception as e:
            return f"""# AI-fejl

Der opstod en fejl ved AI-opfølgning.

Fejl:
{str(e)}

Lokal fallback:

{local_meeting_followup_text(company_name, meeting_title)}
"""

    return f"""# AI ikke aktiveret

OPENAI_API_KEY er ikke sat på computeren.

Systemet bruger derfor lokal opfølgningsskabelon.

{local_meeting_followup_text(company_name, meeting_title)}
"""


def local_meeting_followup_text(company_name, meeting_title):
    return f"""# Opfølgning: {company_name}

## Kort møderesume
- Gennemgå referatet manuelt og fasthold de vigtigste aftaler.

## Aftalte næste skridt
- Identificér konkrete opfølgningspunkter, ansvarlige personer og frister.

## Åbne spørgsmål
- Hvad mangler at blive verificeret?
- Hvem bør kontaktes næste gang?

## Mulige rådgivningsmuligheder
- Vurdér om der er behov for regulatorisk, strategisk eller kvalitetsmæssig sparring.

## Foreslået konkret opfølgning
- Opret relevante noter, observationer eller mødeopgaver ud fra referatet.
"""
