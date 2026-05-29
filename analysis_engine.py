import os, re
from dotenv import load_dotenv

load_dotenv()

SCORE_ORDER = {"Lav": 10, "Middel": 50, "Høj": 80, "Kritisk": 100}

def rule_based_analyze(text, company_name, rules):
    combined = text.lower()
    best = {"trigger_type": "Generelt signal", "score": "Lav", "numeric_score": 10}
    for rule in rules:
        pattern = rule["pattern"]
        try:
            hit = re.search(pattern, text, flags=re.IGNORECASE)
        except re.error:
            hit = any(part.strip().lower() in combined for part in pattern.split("|"))
        if hit and int(rule["weight"]) > best["numeric_score"]:
            best = {
                "trigger_type": rule["name"],
                "score": rule["default_score"],
                "numeric_score": int(rule["weight"])
            }

    if company_name.lower() in combined and best["numeric_score"] < 40:
        best["score"] = "Middel"
        best["numeric_score"] = 40

    title = text[:220].replace("\n", " ")
    best["ai_summary"] = f"Fund vedrørende {company_name}: {title}"
    if best["score"] in ("Kritisk", "Høj"):
        best["suggested_reaction"] = "Gennemgå kilden, vurder om der er en myndigheds-/tillidsdimension, og overvej diskret netværksmæssig opfølgning."
        best["contact_strategy"] = "Kontakt kun via relevant relation eller varm introduktion; positionér som sparring om myndighedsforståelse og næste skridt."
    elif best["score"] == "Middel":
        best["suggested_reaction"] = "Gem som markedsignal og følg udviklingen."
        best["contact_strategy"] = "Ingen direkte kontakt endnu, medmindre der allerede findes en relation."
    else:
        best["suggested_reaction"] = "Arkivér som lavprioritetssignal."
        best["contact_strategy"] = "Ingen kontakt."
    return best

def openai_analyze(text, company_name, rules):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        rules_text = "\n".join([f"- {r['name']}: {r['pattern']} => {r['default_score']}" for r in rules])
        prompt = f"""
Du analyserer passive markeds- og myndighedssignaler for Frank Bøgh Madsen Advisory.
Virksomhed: {company_name}

Triggerregler:
{rules_text}

Kildetekst:
{text[:6000]}

Returnér KUN JSON med felterne:
trigger_type, score, numeric_score, ai_summary, suggested_reaction, contact_strategy.
Score skal være Lav, Middel, Høj eller Kritisk.
"""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )
        import json
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json\n","",1)
        return json.loads(content)
    except Exception:
        return None

def analyze_signal(text, company_name, rules):
    ai = openai_analyze(text, company_name, rules)
    if ai:
        return ai
    return rule_based_analyze(text, company_name, rules)