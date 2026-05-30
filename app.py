
import streamlit as st
from datetime import datetime, date, timedelta
from pathlib import Path
from db import init_db, fetch_df, execute, connect, DATA_DIR, UPLOAD_DIR
from monitor import run_monitor

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ACTOR_TYPES = [
    "Life science-virksomhed",
    "Apotek",
    "Brancheforening",
    "Person / relation",
    "Myndighed",
    "Rådgiver / partner",
    "Andet",
]

def ai_briefing_text(company_name, context_text):
    """AI briefing via OpenAI with local fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

            prompt = f"""
Du er senior strategisk rådgiver for Frank Bøgh Madsen Advisory.

Lav en konkret, kortfattet og professionel mødeforberedelse på dansk til et kommende møde med virksomheden: {company_name}.

Brug kun oplysninger fra konteksten nedenfor.
Du må gerne:
- sammenholde oplysninger
- identificere mønstre
- foreslå relevante spørgsmål
- pege på forhold der bør verificeres
- pege på mulige regulatoriske eller strategiske risici/muligheder

Du må IKKE opfinde fakta.

Struktur:
# Situationsbillede
# Centrale opfølgningspunkter
# Observationer der bør verificeres
# Mulige spørgsmål til mødet
# Potentielle rådgivningsmuligheder
# Frister og næste skridt

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
                            "content": "Du er en præcis dansk advisory-assistent. Brug kun den givne kontekst."
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

## Situationsbillede
- Gennemgå seneste møder, observationer, signaler og historiske sager.
- Fokusér især på oplysninger markeret som ikke verificeret eller bør verificeres.

## Centrale opfølgningspunkter
- Hvad blev aftalt sidst?
- Er der åbne opfølgningspunkter eller frister?
- Er der personer eller relationer, der bør aktiveres?

## Mulige spørgsmål til mødet
- Hvilke kvalitetsmæssige eller regulatoriske forhold fylder mest lige nu?
- Hvad er ændret siden sidst i organisation, QA/RA/GMP eller ledelse?
- Er der konkrete projekter eller frister hvor ekstern sparring kan skabe værdi?

## Potentielle rådgivningsmuligheder
- Strategisk sparring om myndighedsdialog
- Gennemgang af regulatoriske problemstillinger
- Forberedelse til inspektioner eller opfølgning
- Overblik over risici og næste skridt
"""

def ai_meeting_followup_text(company_name, meeting_title, meeting_text, context_text):
    """AI follow-up from meeting minutes with local fallback."""
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

try:
    from document_utils import extract_text_from_file, simple_meeting_summary
except Exception:
    extract_text_from_file = None
    simple_meeting_summary = None

st.set_page_config(page_title="Frank Advisory Intelligence Monitor v2.4", layout="wide")
init_db()

def q(sql, params=()):
    return fetch_df(sql, params)

def run(sql, params=()):
    execute(sql, params)

def display_date(value):
    if not value:
        return ""
    s = str(value)
    try:
        dt = datetime.fromisoformat(s.replace("Z", ""))
        return dt.strftime("%d-%m-%Y")
    except Exception:
        pass
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        return f"{s[8:10]}-{s[5:7]}-{s[0:4]}"
    return s

def now_iso():
    return datetime.utcnow().isoformat()

def short(text, n=900):
    text = text or ""
    return text if len(text) <= n else text[:n] + "..."

def field_label(name):
    labels = {
        "summary": "Resume",
        "key_takeaways": "Hvad lærte vi",
        "next_steps": "Næste skridt / frister",
        "raw_text": "Referattekst",
        "ai_summary": "AI-resume",
        "raw_summary": "Kilderesume",
        "content": "Indhold",
        "implication": "Mulig betydning",
        "follow_up": "Opfølgning",
        "significance": "Betydning",
        "current_relevance": "Nuværende relevans",
        "note": "Note",
        "briefing_text": "Briefing",
        "user_notes": "Egne noter",
    }
    return labels.get(name, name.replace("_", " ").capitalize())

def severity_index(value, options):
    return options.index(value) if value in options else 0

def count_for(table, company_id):
    try:
        return int(q(f"SELECT COUNT(*) AS n FROM {table} WHERE company_id=?", (company_id,))["n"].iloc[0])
    except Exception:
        return 0

def latest_meeting_id(company_id):
    df = q(
        "SELECT id FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC LIMIT 1",
        (company_id,),
    )
    if len(df):
        return int(df["id"].iloc[0])
    return None

def meeting_options(company_id, selected_id=None):
    meetings = q(
        "SELECT id, meeting_date, meeting_time, title FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC",
        (company_id,),
    )
    labels = ["Ingen mødekobling"]
    values = {"Ingen mødekobling": None}
    for _, meeting in meetings.iterrows():
        when = display_date(meeting["meeting_date"]) or "Ukendt dato"
        if meeting["meeting_time"]:
            when += f" kl. {meeting['meeting_time']}"
        label = f"{when} - {meeting['title'] or 'Møde'}"
        values[label] = int(meeting["id"])
        labels.append(label)

    selected_label = "Ingen mødekobling"
    if selected_id:
        for label, value in values.items():
            if value == int(selected_id):
                selected_label = label
                break
    return labels, values, labels.index(selected_label)

def meeting_focus_context(company_id, meeting_id):
    if not meeting_id:
        return ""
    meeting = q(
        """SELECT meeting_date, meeting_time, location, title, meeting_type, participants,
                  summary, key_takeaways, next_steps, raw_text
           FROM meetings WHERE company_id=? AND id=?""",
        (company_id, int(meeting_id)),
    )
    if not len(meeting):
        return ""
    row = meeting.iloc[0]
    parts = ["\n## Møde der forberedes"]
    for col in meeting.columns:
        val = row[col]
        if val:
            parts.append(f"{col}: {val}")
    return "\n".join(parts)

def add_timeline_rows(items, df, item_type, date_col, title_col, body_cols, meta_cols=None):
    meta_cols = meta_cols or []
    if not len(df):
        return
    for _, row in df.iterrows():
        date_value = row.get(date_col, "") or row.get("created_at", "")
        title = row.get(title_col, "") or item_type
        details = []
        body_parts = []
        for col in body_cols:
            value = str(row.get(col, "") or "").strip()
            if value:
                label = field_label(col)
                details.append((label, value))
                body_parts.append(value)
        meta_parts = [str(row.get(col, "")).strip() for col in meta_cols if row.get(col, "")]
        items.append({
            "sort_date": str(date_value or ""),
            "date": date_value,
            "type": item_type,
            "title": title,
            "body": "\n\n".join(body_parts),
            "details": details,
            "meta": " · ".join(meta_parts),
        })

def company_timeline(company_id):
    items = []
    add_timeline_rows(
        items,
        q("""SELECT meeting_date, meeting_time, location, title, meeting_type, participants, summary, key_takeaways, next_steps, raw_text, uploaded_filename, created_at
             FROM meetings WHERE company_id=?""", (company_id,)),
        "Møde",
        "meeting_date",
        "title",
        ["summary", "key_takeaways", "next_steps", "raw_text"],
        ["meeting_time", "location", "meeting_type", "uploaded_filename"],
    )
    add_timeline_rows(
        items,
        q("""SELECT collected_at, title, trigger_type, score, review_status, ai_summary, raw_summary
             FROM signals WHERE company_id=?""", (company_id,)),
        "Signal",
        "collected_at",
        "title",
        ["ai_summary", "raw_summary"],
        ["trigger_type", "score", "review_status"],
    )
    add_timeline_rows(
        items,
        q("""SELECT observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, created_at
             FROM observations WHERE company_id=?""", (company_id,)),
        "Observation",
        "observation_date",
        "title",
        ["content", "implication", "follow_up"],
        ["observation_type", "source_type", "confidence", "verification_status"],
    )
    add_timeline_rows(
        items,
        q("""SELECT period_start, title, case_type, severity, relevance, status, summary, significance, current_relevance, created_at
             FROM company_cases WHERE company_id=?""", (company_id,)),
        "Sag",
        "period_start",
        "title",
        ["summary", "significance", "current_relevance"],
        ["case_type", "severity", "relevance", "status"],
    )
    add_timeline_rows(
        items,
        q("SELECT created_at, title, note FROM notes WHERE company_id=?", (company_id,)),
        "Note",
        "created_at",
        "title",
        ["note"],
    )
    add_timeline_rows(
        items,
        q("SELECT created_at, memory_type, title, content, confidence FROM intelligence_memory WHERE company_id=?", (company_id,)),
        "Videnbank",
        "created_at",
        "title",
        ["content"],
        ["memory_type", "confidence"],
    )
    add_timeline_rows(
        items,
        q("""SELECT b.created_at, b.title, b.briefing_text, b.user_notes, b.version, b.status,
                    CASE
                        WHEN m.id IS NOT NULL THEN COALESCE(m.meeting_date, '') || ' - ' || COALESCE(m.title, 'Møde')
                        ELSE ''
                    END AS linked_meeting
             FROM briefings b
             LEFT JOIN meetings m ON m.id=b.meeting_id
             WHERE b.company_id=?""", (company_id,)),
        "Briefing",
        "created_at",
        "title",
        ["briefing_text", "user_notes"],
        ["linked_meeting", "version", "status"],
    )
    add_timeline_rows(
        items,
        q("""SELECT created_at, due_date, title, description, person, priority, status, source_type
             FROM followups WHERE company_id=?""", (company_id,)),
        "Opfølgning",
        "due_date",
        "title",
        ["description"],
        ["person", "priority", "status", "source_type"],
    )
    return sorted(items, key=lambda item: item["sort_date"] or "", reverse=True)

def set_page(name):
    st.session_state["page"] = name

def set_company(company_id):
    st.session_state["selected_company_id"] = int(company_id)
    st.session_state["force_profile_view"] = True

def open_company_section(company_id, section):
    st.session_state["selected_company_id"] = int(company_id)
    st.session_state[f"profile_section_{int(company_id)}"] = section
    st.session_state["force_profile_view"] = True
    st.session_state["page"] = "Virksomheder"

def followup_group(row, today_iso):
    due = str(row.get("due_date", "") or "").strip()
    if not due:
        return "Uden dato"
    if len(due) >= 10 and due[4:5] == "-" and due[7:8] == "-":
        try:
            due_date = date.fromisoformat(due[:10])
            today_date = date.fromisoformat(today_iso)
            if due_date < today_date:
                return "Forfaldne"
            if due_date <= today_date + timedelta(days=30):
                return "Næste 30 dage"
        except ValueError:
            pass
    return "Planlagt senere"

def briefing_context(company_id):
    parts = []
    company = q("SELECT * FROM companies WHERE id=?", (company_id,))
    if len(company):
        r = company.iloc[0]
        parts.append(f"Virksomhed: {r['name']}")
        parts.append(f"Aktørtype: {r.get('actor_type','') if hasattr(r,'get') else r['actor_type']}")
        parts.append(f"Kategori: {r.get('category','') if hasattr(r,'get') else r['category']}")
    for label, sql in [
        ("Seneste møder", "SELECT meeting_date, meeting_time, location, title, participants, summary, key_takeaways, next_steps FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC LIMIT 10"),
        ("Åbne opfølgninger / leads", "SELECT due_date, title, description, person, priority, status, source_type FROM followups WHERE company_id=? AND COALESCE(status,'Ny') NOT IN ('Lukket','Arkiveret') ORDER BY due_date ASC, created_at DESC LIMIT 15"),
        ("Observationer", "SELECT observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up FROM observations WHERE company_id=? ORDER BY observation_date DESC, created_at DESC LIMIT 15"),
        ("Historik / sager", "SELECT title, case_type, period_start, period_end, severity, relevance, status, summary, significance, current_relevance FROM company_cases WHERE company_id=? ORDER BY period_start DESC, created_at DESC LIMIT 10"),
        ("Signaler", "SELECT collected_at, title, trigger_type, score, review_status, ai_summary, review_note FROM signals WHERE company_id=? ORDER BY collected_at DESC LIMIT 15"),
        ("Videnbank", "SELECT memory_type, title, content, confidence, created_at FROM intelligence_memory WHERE company_id=? ORDER BY created_at DESC LIMIT 15"),
        ("Noter", "SELECT title, note, created_at FROM notes WHERE company_id=? ORDER BY created_at DESC LIMIT 15")
    ]:
        df = q(sql, (company_id,))
        if len(df):
            parts.append(f"\n## {label}")
            for _, row in df.iterrows():
                vals = []
                for col in df.columns:
                    val = row[col]
                    if val:
                        vals.append(f"{col}: {val}")
                parts.append("- " + " | ".join(vals))
    return "\n".join(parts)


def save_uploaded_file(company_id, uploaded_file):
    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    folder = UPLOAD_DIR / str(company_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return target

st.markdown("""
<style>
div.stButton > button { min-height: 2.35rem; font-size: 0.95rem; }
[data-testid="stDataFrame"] { font-size: 0.88rem; }
.small-muted { color: #777; font-size: 0.85rem; }
.company-row { border-bottom: 1px solid #eee; padding: 0.15rem 0; }
</style>
""", unsafe_allow_html=True)

page_options = ["Dashboard", "Signalindbakke", "Virksomheder", "Briefing", "Kilder", "Triggerregler"]
if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"
if st.session_state["page"] not in page_options:
    st.session_state["page"] = "Dashboard"

st.title("Frank Advisory Intelligence Monitor v2.4")
st.caption("Advisory intelligence, virksomhedsprofiler og mødeforberedelse")

with st.sidebar:
    st.caption(f"Data: {DATA_DIR}")
    chosen = st.radio("Vælg visning", page_options, index=page_options.index(st.session_state["page"]))
    if chosen != st.session_state["page"]:
        st.session_state["page"] = chosen
        st.rerun()
    if st.button("Kør overvågning nu", type="primary"):
        with st.spinner("Overvåger kilder..."):
            result = run_monitor()
        st.success(f"Færdig. Fund indsamlet: {result['collected']}. Relevante signaler: {result['relevant']}.")

page = st.session_state["page"]

if page == "Dashboard":
    today_iso = date.today().isoformat()
    signals = q("""SELECT s.id, s.collected_at, c.name AS company, s.trigger_type, s.score,
                          s.title, COALESCE(s.review_status,'Ny') AS review_status
                   FROM signals s LEFT JOIN companies c ON c.id=s.company_id
                   ORDER BY s.collected_at DESC""")
    companies = q("SELECT * FROM companies")
    meetings = q("SELECT m.*, c.name AS company FROM meetings m LEFT JOIN companies c ON c.id=m.company_id ORDER BY m.meeting_date ASC, m.meeting_time ASC")
    observations = q("SELECT * FROM observations")
    followups = q("""SELECT f.*, c.name AS company
                     FROM followups f LEFT JOIN companies c ON c.id=f.company_id
                     WHERE COALESCE(f.status, 'Ny') NOT IN ('Lukket', 'Arkiveret')
                     ORDER BY
                        CASE f.priority WHEN 'Høj' THEN 1 WHEN 'Middel' THEN 2 ELSE 3 END,
                        CASE WHEN f.due_date='' OR f.due_date IS NULL THEN 1 ELSE 0 END,
                        f.due_date ASC,
                        f.created_at DESC""")
    if len(followups):
        followups["dashboard_group"] = followups.apply(lambda row: followup_group(row, today_iso), axis=1)
    upcoming = q("""SELECT m.id, m.company_id, m.meeting_date, m.meeting_time, m.location, m.title, c.name AS company
                    FROM meetings m LEFT JOIN companies c ON c.id=m.company_id
                    WHERE m.meeting_date >= ?
                    ORDER BY m.meeting_date ASC, m.meeting_time ASC
                    LIMIT 8""", (today_iso,))
    overdue_count = int((followups["dashboard_group"] == "Forfaldne").sum()) if len(followups) else 0
    next30_count = int((followups["dashboard_group"] == "Næste 30 dage").sum()) if len(followups) else 0
    new_signal_count = int((signals["review_status"] == "Ny").sum()) if len(signals) else 0
    cols = st.columns(5)
    cols[0].metric("Forfaldne", overdue_count)
    cols[1].metric("Næste 30 dage", next30_count)
    cols[2].metric("Kommende møder", len(upcoming))
    cols[3].metric("Nye signaler", new_signal_count)
    cols[4].metric("Åbne leads", len(followups))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Dashboard · {display_date(date.today().isoformat())}")
        st.markdown("### Dagens fokus")
        if overdue_count:
            st.warning(f"{overdue_count} opfølgning(er) er forfaldne.")
        elif next30_count:
            st.info(f"{next30_count} opfølgning(er) ligger inden for de næste 30 dage.")
        else:
            st.success("Ingen daterede opfølgninger kræver akut handling.")
        if len(upcoming):
            next_meeting = upcoming.iloc[0]
            when = display_date(next_meeting["meeting_date"])
            if next_meeting["meeting_time"]:
                when += f" kl. {next_meeting['meeting_time']}"
            st.markdown(f"**Næste møde:** {when} — {next_meeting['company'] or 'Ukendt aktør'}")
            st.caption(next_meeting["title"] or "Møde")
        if new_signal_count:
            st.caption(f"{new_signal_count} nye signaler bør gennemgås i Signalindbakken.")

        with st.expander("Tilføj opfølgning / lead", expanded=False):
            with st.form(f"dashboard_add_followup_{st.session_state.get('dashboard_followup_form_version',0)}", clear_on_submit=True):
                company_labels = ["Ingen aktør"] + companies["name"].tolist() if len(companies) else ["Ingen aktør"]
                selected_company = st.selectbox("Aktør", company_labels)
                title = st.text_input("Titel", value="")
                person = st.text_input("Person", value="")
                due_date = st.text_input("Dato/timing", value="")
                priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
                description = st.text_area("Beskrivelse", value="", height=120)
                if st.form_submit_button("Gem opfølgning"):
                    selected_company_id = None
                    if selected_company != "Ingen aktør" and len(companies):
                        selected_company_id = int(companies[companies["name"] == selected_company]["id"].iloc[0])
                    run(
                        """INSERT INTO followups
                           (company_id, title, description, person, due_date, priority, status, source_type, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (selected_company_id, title, description, person, due_date, priority, status, "Dashboard", now_iso(), now_iso()),
                    )
                    st.session_state["dashboard_followup_form_version"] = st.session_state.get("dashboard_followup_form_version",0) + 1
                    st.success("Opfølgning gemt.")
                    st.rerun()

        st.markdown("### Næste handlinger / leads")
        if len(followups):
            for group_name in ["Forfaldne", "Næste 30 dage", "Uden dato", "Planlagt senere"]:
                group_df = followups[followups["dashboard_group"] == group_name]
                if len(group_df):
                    st.markdown(f"**{group_name} ({len(group_df)})**")
                    for _, f in group_df.head(6).iterrows():
                        with st.container(border=True):
                            due = display_date(f["due_date"]) if f["due_date"] else "Ingen dato"
                            company = f["company"] or "Ingen virksomhed"
                            person = f" · {f['person']}" if f["person"] else ""
                            st.markdown(f"**{f['title']}**")
                            st.caption(f"{company}{person} · {due} · {f['priority']} · {f['status']}")
                            if f["description"]:
                                st.write(short(f["description"], 220))
                            a, b, c = st.columns(3)
                            if a.button("Åbn profil", key=f"dash_follow_open_{int(f['id'])}", disabled=not f["company_id"]):
                                open_company_section(int(f["company_id"]), "Opfølgning")
                                st.rerun()
                            if b.button("I gang", key=f"dash_follow_progress_{int(f['id'])}"):
                                run("UPDATE followups SET status=?, updated_at=? WHERE id=?", ("I gang", now_iso(), int(f["id"])))
                                st.rerun()
                            if c.button("Luk", key=f"dash_follow_close_{int(f['id'])}"):
                                run("UPDATE followups SET status=?, updated_at=? WHERE id=?", ("Lukket", now_iso(), int(f["id"])))
                                st.rerun()
        else:
            st.success("Ingen åbne opfølgninger.")

        st.markdown("### Signalpåmindelse")
        new_count = int((signals["review_status"] == "Ny").sum()) if len(signals) else 0
        review_count = int((signals["review_status"] == "Til vurdering").sum()) if len(signals) else 0
        if new_count or review_count:
            st.info(f"Der er {new_count} nye signaler og {review_count} signaler til vurdering.")
        else:
            st.success("Ingen nye signaler kræver behandling.")
        if st.button("Gå til Signalindbakke"):
            set_page("Signalindbakke")
            st.rerun()
    with c2:
        st.subheader("Kommende møder / husketing")
        if len(upcoming):
            for _, m in upcoming.iterrows():
                with st.container(border=True):
                    when = display_date(m["meeting_date"])
                    if m["meeting_time"]:
                        when += f" kl. {m['meeting_time']}"
                    st.markdown(f"**{when} — {m['company'] or 'Ukendt aktør'}**")
                    st.caption(f"{m['title'] or 'Møde'}" + (f" · {m['location']}" if m["location"] else ""))
                    a, b = st.columns(2)
                    if a.button("Åbn profil", key=f"dash_meeting_profile_{int(m['id'])}", disabled=not m["company_id"]):
                        open_company_section(int(m["company_id"]), "Møder")
                        st.rerun()
                    if b.button("Briefing", key=f"dash_meeting_briefing_{int(m['id'])}", disabled=not m["company_id"]):
                        st.session_state["selected_company_id"] = int(m["company_id"])
                        st.session_state["selected_briefing_meeting_id"] = int(m["id"])
                        set_page("Briefing")
                        st.rerun()
        else:
            st.caption("Ingen kommende møder registreret.")

    st.subheader("Mødeforberedelse")
    st.caption("Brug kommende møder som anledning til at samle tidligere aftaler, observationer og åbne opfølgningspunkter.")

elif page == "Signalindbakke":
    st.subheader("Signalindbakke")
    df = q("""SELECT s.id, s.collected_at, c.name AS company, s.trigger_type, s.score,
                     s.title, s.raw_summary, s.source_excerpt, s.matched_terms, s.ai_summary,
                     s.suggested_reaction, COALESCE(s.review_status,'Ny') AS review_status,
                     s.review_note, s.url
              FROM signals s LEFT JOIN companies c ON c.id=s.company_id
              ORDER BY s.collected_at DESC""")
    f1, f2, f3 = st.columns(3)
    status_filter = f1.multiselect("Status", ["Ny","Til vurdering","Gemt på virksomhed","Irrelevant","Arkiveret"], default=["Ny","Til vurdering"])
    score_filter = f2.multiselect("Score", ["Lav","Middel","Høj","Kritisk"], default=["Lav","Middel","Høj","Kritisk"])
    search = f3.text_input("Søg")
    if len(df):
        df = df[df["review_status"].isin(status_filter)]
        df = df[df["score"].isin(score_filter)]
        if search:
            df = df[df["company"].fillna("").str.contains(search, case=False, na=False) | df["title"].fillna("").str.contains(search, case=False, na=False)]
    if len(df):
        for _, r in df.iterrows():
            with st.container(border=True):
                st.markdown(f"### {r['company'] or 'Ukendt'}")
                st.markdown(f"**{r['title']}**")
                st.caption(f"Dato: {display_date(r['collected_at'])} · Trigger: {r['trigger_type']} · Score: {r['score']} · Status: {r['review_status']}")
                if r["matched_terms"]:
                    st.write(f"**Match:** {r['matched_terms']}")
                preview = r["source_excerpt"] or r["ai_summary"] or r["raw_summary"] or ""
                if preview:
                    st.write(short(preview, 1400))
                if r["suggested_reaction"]:
                    st.write(f"**Foreløbig vurdering:** {r['suggested_reaction']}")
                if r["review_note"]:
                    st.info(f"Note: {r['review_note']}")
                btns = st.columns([1,1,1,1,1,2])
                if btns[0].button("Til vurdering", key=f"sig_review_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Til vurdering", int(r["id"]))); st.rerun()
                if btns[1].button("Gem", key=f"sig_save_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Gemt på virksomhed", int(r["id"]))); st.rerun()
                if btns[2].button("Irrelevant", key=f"sig_irr_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Irrelevant", int(r["id"]))); st.rerun()
                if btns[3].button("Arkivér", key=f"sig_arch_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Arkiveret", int(r["id"]))); st.rerun()
                if btns[4].button("Slet", key=f"sig_del_{r['id']}"):
                    run("DELETE FROM signals WHERE id=?", (int(r["id"]),)); st.rerun()
                if r["url"]:
                    btns[5].link_button("Åbn kilde", r["url"])
                with st.expander("Ret behandlingsnote"):
                    note = st.text_area("Note", value=r["review_note"] or "", key=f"sig_note_{r['id']}")
                    if st.button("Gem note", key=f"sig_note_save_{r['id']}"):
                        run("UPDATE signals SET review_note=? WHERE id=?", (note, int(r["id"]))); st.rerun()
    else:
        st.info("Ingen signaler matcher filteret.")

elif page == "Virksomheder":
    st.subheader("Virksomheder")
    companies = q("SELECT * FROM companies ORDER BY name")
    if st.session_state.pop("force_profile_view", False):
        st.session_state["company_view_mode"] = "Profil"
    if st.session_state.get("company_view_mode") not in ["Oversigt", "Profil"]:
        st.session_state["company_view_mode"] = "Oversigt"
    mode = st.radio("Visning", ["Oversigt", "Profil"], horizontal=True, key="company_view_mode")

    if mode == "Oversigt":
        f1, f2, f3, f4 = st.columns([1,1,1.4,2])
        status_filter = f1.multiselect("Status", ["Aktiv","Pauset","Arkiveret"], default=["Aktiv","Pauset"])
        priority_filter = f2.multiselect("Prioritet", ["Lav","Middel","Høj"], default=["Lav","Middel","Høj"])
        type_filter = f3.multiselect("Aktørtype", ACTOR_TYPES, default=ACTOR_TYPES)
        search = f4.text_input("Søg i virksomheder")
        shown = companies.copy()
        if len(shown):
            shown = shown[shown["status"].isin(status_filter)]
            shown = shown[shown["priority"].isin(priority_filter)]
            shown = shown[shown["actor_type"].fillna("Life science-virksomhed").isin(type_filter)]
            if search:
                shown = shown[shown["name"].fillna("").str.contains(search, case=False, na=False) |
                              shown["actor_type"].fillna("").str.contains(search, case=False, na=False) |
                              shown["category"].fillna("").str.contains(search, case=False, na=False) |
                              shown["aliases"].fillna("").str.contains(search, case=False, na=False)]
        if len(shown):
            for _, r in shown.iterrows():
                cols = st.columns([0.8,2.5,1.7,2,1,1])
                if cols[0].button("Åbn", key=f"open_company_{int(r['id'])}"):
                    set_company(int(r["id"]))
                    st.rerun()
                cols[1].markdown(f"**{r['name']}**")
                cols[2].caption(r["actor_type"] or "Life science-virksomhed")
                cols[3].caption(r["category"] or "")
                cols[4].caption(r["priority"] or "")
                cols[5].caption(r["status"] or "")
        else:
            st.info("Ingen virksomheder matcher filteret.")

    else:
        if len(companies) == 0:
            st.info("Ingen virksomheder.")
        else:
            ids = companies["id"].tolist()
            default_id = st.session_state.get("selected_company_id", ids[0])
            idx = ids.index(default_id) if default_id in ids else 0
            selected_name = st.selectbox("Vælg virksomhed", companies["name"].tolist(), index=idx)
            company_id = int(companies[companies["name"] == selected_name]["id"].iloc[0])
            st.session_state["selected_company_id"] = company_id
            row = q("SELECT * FROM companies WHERE id=?", (company_id,)).iloc[0]

            st.markdown(f"## {row['name']}")
            meta = st.columns(4)
            meta[0].metric("Aktørtype", row["actor_type"] or "Life science-virksomhed")
            meta[1].metric("Kategori", row["category"] or "—")
            meta[2].metric("Prioritet", row["priority"] or "—")
            meta[3].metric("Status", row["status"] or "—")
            links = []
            if row["website"]: links.append(f"[Website]({row['website']})")
            if row["linkedin"]: links.append(f"[LinkedIn]({row['linkedin']})")
            if links: st.markdown(" · ".join(links))

            sig_n = count_for("signals", company_id)
            meet_n = count_for("meetings", company_id)
            obs_n = count_for("observations", company_id)
            case_n = count_for("company_cases", company_id)
            contact_n = count_for("contacts", company_id)
            note_n = count_for("notes", company_id)
            mem_n = count_for("intelligence_memory", company_id)
            brief_n = count_for("briefings", company_id)
            follow_n = count_for("followups", company_id)
            timeline_n = sig_n + meet_n + obs_n + case_n + note_n + mem_n + brief_n + follow_n

            section_counts = {
                "Tidslinje": timeline_n,
                "Opfølgning": follow_n,
                "Signaler": sig_n,
                "Møder": meet_n,
                "Observationer": obs_n,
                "Historik / Sager": case_n,
                "Kontakter": contact_n,
                "Noter": note_n,
                "Videnbank": mem_n,
                "Briefing": brief_n,
            }
            sections = ["Tidslinje", "Opfølgning", "Signaler", "Møder", "Observationer", "Historik / Sager", "Kontakter", "Noter", "Videnbank", "Briefing"]
            section_key = f"profile_section_{company_id}"
            if st.session_state.get(section_key) not in sections:
                st.session_state[section_key] = "Tidslinje"
            section_base = st.radio(
                "Profilsektion",
                sections,
                horizontal=True,
                key=section_key,
                format_func=lambda name: f"{name} ({section_counts[name]})" if name in section_counts else name,
            )

            with st.expander("Redigér virksomhedsdata"):
                with st.form("edit_company_form"):
                    name = st.text_input("Navn", row["name"])
                    actor_type = st.selectbox(
                        "Aktørtype",
                        ACTOR_TYPES,
                        index=severity_index(row["actor_type"] or "Life science-virksomhed", ACTOR_TYPES),
                    )
                    category = st.text_area("Kategori", row["category"] or "", height=80)
                    country = st.text_input("Land", row["country"] or "Danmark")
                    priority = st.selectbox("Prioritet", ["Lav","Middel","Høj"], index=severity_index(row["priority"], ["Lav","Middel","Høj"]))
                    status = st.selectbox("Status", ["Aktiv","Pauset","Arkiveret"], index=severity_index(row["status"], ["Aktiv","Pauset","Arkiveret"]))
                    aliases = st.text_input("Aliaser", row["aliases"] or "")
                    website = st.text_input("Website", row["website"] or "")
                    linkedin = st.text_input("LinkedIn", row["linkedin"] or "")
                    if st.form_submit_button("Gem virksomhed"):
                        run("UPDATE companies SET name=?, actor_type=?, category=?, country=?, priority=?, status=?, aliases=?, website=?, linkedin=? WHERE id=?",
                            (name, actor_type, category, country, priority, status, aliases, website, linkedin, company_id)); st.rerun()

            if section_base == "Tidslinje":
                st.markdown("### Samlet virksomhedstidslinje")
                timeline = company_timeline(company_id)
                if timeline:
                    for item in timeline:
                        with st.container(border=True):
                            date_text = display_date(item["date"]) or "Ukendt dato"
                            st.markdown(f"**{date_text} · {item['type']} · {item['title']}**")
                            if item["meta"]:
                                st.caption(item["meta"])
                            if item["body"]:
                                st.write(short(item["body"], 900))
                                if len(item["body"]) > 900:
                                    with st.expander("Vis hele indholdet"):
                                        for label, value in item["details"]:
                                            st.markdown(f"**{label}**")
                                            st.text_area(
                                                label,
                                                value,
                                                height=260,
                                                key=f"timeline_detail_{company_id}_{item['type']}_{item['sort_date']}_{label}_{abs(hash(value))}",
                                                disabled=True,
                                            )
                else:
                    st.info("Ingen tidslinjeelementer endnu.")

            elif section_base == "Opfølgning":
                st.markdown("### Opfølgninger / leads")
                followups = q("SELECT * FROM followups WHERE company_id=? ORDER BY due_date ASC, created_at DESC", (company_id,))
                if len(followups):
                    for _, f in followups.iterrows():
                        with st.container(border=True):
                            due = display_date(f["due_date"]) if f["due_date"] else "Ingen dato"
                            st.markdown(f"**{f['title']}**")
                            meta = [due, f["priority"], f["status"], f["source_type"]]
                            if f["person"]:
                                meta.insert(1, f["person"])
                            st.caption(" · ".join([m for m in meta if m]))
                            if f["description"]:
                                st.write(f["description"])
                            with st.expander("Redigér / slet opfølgning"):
                                with st.form(f"edit_followup_{int(f['id'])}"):
                                    title = st.text_input("Titel", f["title"])
                                    description = st.text_area("Beskrivelse", f["description"] or "", height=120)
                                    person = st.text_input("Person", f["person"] or "")
                                    due_date = st.text_input("Dato/timing", f["due_date"] or "")
                                    priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=severity_index(f["priority"], ["Lav", "Middel", "Høj"]))
                                    status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer", "Lukket", "Arkiveret"], index=severity_index(f["status"], ["Ny", "Planlagt", "I gang", "Afventer", "Lukket", "Arkiveret"]))
                                    a, b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run(
                                            "UPDATE followups SET title=?, description=?, person=?, due_date=?, priority=?, status=?, updated_at=? WHERE id=?",
                                            (title, description, person, due_date, priority, status, now_iso(), int(f["id"])),
                                        )
                                        st.rerun()
                                    if b.form_submit_button("Slet opfølgning"):
                                        run("DELETE FROM followups WHERE id=?", (int(f["id"]),))
                                        st.rerun()
                else:
                    st.info("Ingen opfølgninger endnu.")
                with st.expander("Tilføj opfølgning / lead"):
                    with st.form(f"add_followup_{company_id}_{st.session_state.get('followup_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        description = st.text_area("Beskrivelse", value="", height=120)
                        person = st.text_input("Person", value="")
                        due_date = st.text_input("Dato/timing", value="")
                        priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                        status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
                        if st.form_submit_button("Gem opfølgning"):
                            run(
                                """INSERT INTO followups
                                   (company_id, title, description, person, due_date, priority, status, source_type, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, title, description, person, due_date, priority, status, "Manuel", now_iso(), now_iso()),
                            )
                            st.session_state["followup_form_version"] = st.session_state.get("followup_form_version",0) + 1
                            st.rerun()

            elif section_base == "Signaler":
                sigs = q("SELECT id, collected_at, trigger_type, score, review_status, title FROM signals WHERE company_id=? ORDER BY collected_at DESC", (company_id,))
                if len(sigs):
                    for _, s in sigs.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{s['title']}**")
                            st.caption(f"Dato: {display_date(s['collected_at'])} · {s['trigger_type']} · {s['score']} · {s['review_status']}")
                            c = st.columns([1,1])
                            if c[0].button("Arkivér", key=f"prof_sig_arch_{int(s['id'])}"):
                                run("UPDATE signals SET review_status='Arkiveret' WHERE id=?", (int(s["id"]),)); st.rerun()
                            if c[1].button("Slet", key=f"prof_sig_del_{int(s['id'])}"):
                                run("DELETE FROM signals WHERE id=?", (int(s["id"]),)); st.rerun()
                else:
                    st.info("Ingen signaler.")

            elif section_base == "Møder":
                meetings = q("SELECT * FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC", (company_id,))
                if len(meetings):
                    for _, m in meetings.iterrows():
                        with st.container(border=True):
                            when = display_date(m["meeting_date"])
                            if "meeting_time" in meetings.columns and m["meeting_time"]:
                                when += f" kl. {m['meeting_time']}"
                            st.markdown(f"**{when} — {m['title']}**")
                            extra = []
                            if "location" in meetings.columns and m["location"]: extra.append(m["location"])
                            if m["meeting_type"]: extra.append(m["meeting_type"])
                            if m["relation_strength"]: extra.append(f"Relation: {m['relation_strength']}")
                            st.caption(" · ".join(extra))
                            if m["participants"]: st.write(f"**Deltagere:** {m['participants']}")
                            if m["summary"]: st.write(m["summary"])
                            if m["key_takeaways"]: st.write(f"**Hvad lærte vi:** {m['key_takeaways']}")
                            if m["next_steps"]: st.write(f"**Næste skridt / frister:** {m['next_steps']}")
                            if "uploaded_filename" in meetings.columns and m["uploaded_filename"]:
                                st.caption(f"Uploadet referat: {m['uploaded_filename']}")
                            if "raw_text" in meetings.columns and m["raw_text"]:
                                with st.expander("Vis referattekst"):
                                    st.text_area(
                                        "Referattekst",
                                        m["raw_text"],
                                        height=260,
                                        key=f"meeting_raw_text_{int(m['id'])}",
                                    )
                                followup_key = f"meeting_ai_followup_{int(m['id'])}"
                                if st.button("Lav AI-opfølgning på referat", key=f"generate_followup_{int(m['id'])}"):
                                    st.session_state[followup_key] = ai_meeting_followup_text(
                                        row["name"],
                                        m["title"],
                                        m["raw_text"],
                                        briefing_context(company_id),
                                    )
                                if followup_key in st.session_state:
                                    st.markdown("**AI-opfølgning**")
                                    st.markdown(st.session_state[followup_key])
                                    with st.form(f"save_followup_note_{int(m['id'])}"):
                                        note_title = st.text_input(
                                            "Notetitel",
                                            f"AI-opfølgning - {m['title']} - {m['meeting_date'] or datetime.now().strftime('%Y-%m-%d')}",
                                        )
                                        note_text = st.text_area(
                                            "Opfølgningstekst",
                                            st.session_state[followup_key],
                                            height=240,
                                        )
                                        if st.form_submit_button("Gem som note på virksomheden"):
                                            run(
                                                "INSERT INTO notes (company_id, title, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                                (company_id, note_title, note_text, now_iso(), now_iso()),
                                            )
                                            st.success("AI-opfølgning gemt som note.")
                                    with st.form(f"save_followup_lead_{int(m['id'])}"):
                                        lead_title = st.text_input(
                                            "Lead/opfølgningstitel",
                                            f"Opfølgning - {m['title']}",
                                        )
                                        lead_description = st.text_area(
                                            "Beskrivelse til dashboard",
                                            st.session_state[followup_key],
                                            height=180,
                                        )
                                        lead_person = st.text_input("Person", value="")
                                        lead_due_date = st.text_input("Dato/timing", value="")
                                        lead_priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                                        lead_status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
                                        if st.form_submit_button("Gem som opfølgning / lead"):
                                            run(
                                                """INSERT INTO followups
                                                   (company_id, title, description, person, due_date, priority, status, source_type, source_id, created_at, updated_at)
                                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                                (
                                                    company_id,
                                                    lead_title,
                                                    lead_description,
                                                    lead_person,
                                                    lead_due_date,
                                                    lead_priority,
                                                    lead_status,
                                                    "AI-opfølgning",
                                                    int(m["id"]),
                                                    now_iso(),
                                                    now_iso(),
                                                ),
                                            )
                                            st.success("AI-opfølgning gemt som opfølgning/lead på dashboardet.")
                            with st.expander("Redigér / slet møde"):
                                with st.form(f"edit_meeting_{int(m['id'])}"):
                                    title = st.text_input("Titel", m["title"])
                                    meeting_date = st.text_input("Dato", m["meeting_date"] or "")
                                    meeting_time = st.text_input("Tidspunkt", m["meeting_time"] if "meeting_time" in meetings.columns else "")
                                    location = st.text_input("Adresse/sted", m["location"] if "location" in meetings.columns else "")
                                    participants = st.text_input("Deltagere", m["participants"] or "")
                                    summary = st.text_area("Resume", m["summary"] or "")
                                    key_takeaways = st.text_area("Hvad lærte vi?", m["key_takeaways"] or "")
                                    next_steps = st.text_area("Næste skridt / frister", m["next_steps"] or "")
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE meetings SET title=?, meeting_date=?, meeting_time=?, location=?, participants=?, summary=?, key_takeaways=?, next_steps=?, updated_at=? WHERE id=?",
                                            (title, meeting_date, meeting_time, location, participants, summary, key_takeaways, next_steps, now_iso(), int(m["id"]))); st.rerun()
                                    if b.form_submit_button("Slet møde"):
                                        run("DELETE FROM meetings WHERE id=?", (int(m["id"]),)); st.rerun()
                with st.expander("Tilføj møde", expanded=False):
                    form_key = f"add_meeting_{company_id}_{st.session_state.get('meeting_form_version',0)}"
                    with st.form(form_key, clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        meeting_date = st.text_input("Dato", datetime.now().strftime("%Y-%m-%d"))
                        meeting_time = st.text_input("Tidspunkt", value="")
                        location = st.text_input("Adresse/sted", value="")
                        meeting_type = st.selectbox("Type", ["Kaffemøde","Kundemøde","Netværk","Konference","Telefon","Regulatorisk","Uformelt"])
                        participants = st.text_input("Deltagere", value="")
                        relation_strength = st.selectbox("Relationstyrke", ["Svag","Middel","Stærk","Meget stærk"], index=1)
                        confidentiality = st.selectbox("Fortrolighed", ["Offentlig/OSINT","Intern","Fortrolig","Del ikke eksternt"], index=1)
                        summary = st.text_area("Resume", value="")
                        key_takeaways = st.text_area("Hvad lærte vi?", value="")
                        next_steps = st.text_area("Næste skridt / frister", value="")
                        if st.form_submit_button("Gem møde"):
                            run("""INSERT INTO meetings (company_id, meeting_date, meeting_time, location, title, meeting_type, participants, relation_strength, confidentiality, summary, key_takeaways, next_steps, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, meeting_date, meeting_time, location, title, meeting_type, participants, relation_strength, confidentiality, summary, key_takeaways, next_steps, now_iso(), now_iso()))
                            st.session_state["meeting_form_version"] = st.session_state.get("meeting_form_version",0) + 1
                            st.rerun()
                with st.expander("Upload referat", expanded=False):
                    upload_key = f"upload_{company_id}_{st.session_state.get('upload_version',0)}"
                    uploaded = st.file_uploader("Upload Word, PDF eller TXT", type=["docx","pdf","txt"], key=upload_key)
                    if uploaded and extract_text_from_file:
                        meeting_title = st.text_input("Mødetitel", Path(uploaded.name).stem, key=f"upload_title_{upload_key}")
                        meeting_date = st.text_input("Dato for møde", datetime.now().strftime("%Y-%m-%d"), key=f"upload_date_{upload_key}")
                        meeting_time = st.text_input("Tidspunkt", value="", key=f"upload_time_{upload_key}")
                        location = st.text_input("Adresse/sted", value="", key=f"upload_location_{upload_key}")
                        if st.button("Gem og udtræk tekst", key=f"upload_btn_{upload_key}"):
                            path = save_uploaded_file(company_id, uploaded)
                            extracted = extract_text_from_file(str(path))
                            summary = simple_meeting_summary(extracted) if simple_meeting_summary else {"summary": extracted[:1000], "key_takeaways": "", "next_steps": ""}
                            run("""INSERT INTO meetings (company_id, meeting_date, meeting_time, location, title, meeting_type, confidentiality, shareability, summary, key_takeaways, next_steps, raw_text, uploaded_filename, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, meeting_date, meeting_time, location, meeting_title, "Referat", "Intern", "Kun internt", summary["summary"], summary["key_takeaways"], summary["next_steps"], extracted, uploaded.name, now_iso(), now_iso()))
                            st.session_state["upload_version"] = st.session_state.get("upload_version",0) + 1
                            st.rerun()

            elif section_base == "Observationer":
                observations = q("SELECT * FROM observations WHERE company_id=? ORDER BY observation_date DESC, created_at DESC", (company_id,))
                if len(observations):
                    for _, o in observations.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{o['title']}**")
                            st.caption(f"{display_date(o['observation_date'])} · {o['observation_type']} · {o['source_type']} · {o['confidence']} · {o['verification_status']}")
                            st.write(o["content"])
                            if o["implication"]: st.write(f"**Mulig betydning:** {o['implication']}")
                            if o["follow_up"]: st.write(f"**Opfølgning:** {o['follow_up']}")
                            with st.expander("Redigér / slet observation"):
                                with st.form(f"edit_obs_{int(o['id'])}"):
                                    title = st.text_input("Titel", o["title"])
                                    content = st.text_area("Indhold", o["content"])
                                    implication = st.text_area("Mulig betydning", o["implication"] or "")
                                    follow_up = st.text_area("Opfølgning", o["follow_up"] or "")
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE observations SET title=?, content=?, implication=?, follow_up=?, updated_at=? WHERE id=?",
                                            (title, content, implication, follow_up, now_iso(), int(o["id"]))); st.rerun()
                                    if b.form_submit_button("Slet observation"):
                                        run("DELETE FROM observations WHERE id=?", (int(o["id"]),)); st.rerun()
                with st.expander("Tilføj observation / rygte / signal"):
                    with st.form(f"add_observation_{company_id}_{st.session_state.get('obs_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        observation_date = st.text_input("Dato", datetime.now().strftime("%Y-%m-%d"))
                        observation_type = st.selectbox("Type", ["Observation","Rygte","Mødesignal","OSINT-signal","Relation","Risiko","Mulighed"])
                        source_type = st.selectbox("Kilde", ["OSINT","Kaffemøde","Konkurrent","Relation","Tidligere erfaring","Andet"])
                        confidence = st.selectbox("Tillid", ["Lav","Middel","Høj"], index=1)
                        verification_status = st.selectbox("Verifikation", ["Ikke verificeret","Bør verificeres","Delvist verificeret","Verificeret"], index=0)
                        content = st.text_area("Indhold", value="")
                        implication = st.text_area("Mulig betydning", value="")
                        follow_up = st.text_area("Opfølgning", value="")
                        if st.form_submit_button("Gem observation"):
                            run("""INSERT INTO observations (company_id, observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, now_iso(), now_iso()))
                            st.session_state["obs_form_version"] = st.session_state.get("obs_form_version",0) + 1
                            st.rerun()

            elif section_base == "Historik / Sager":
                cases = q("SELECT * FROM company_cases WHERE company_id=? ORDER BY period_start DESC, created_at DESC", (company_id,))
                if len(cases):
                    for _, c in cases.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{c['title']}**")
                            st.caption(f"{c['case_type']} · {c['severity']} · relevans {c['relevance']} · {c['status']}")
                            if c["summary"]: st.write(c["summary"])
                            with st.expander("Redigér / slet sag"):
                                with st.form(f"edit_case_{int(c['id'])}"):
                                    title = st.text_input("Titel", c["title"])
                                    summary = st.text_area("Resume", c["summary"] or "")
                                    significance = st.text_area("Betydning", c["significance"] or "")
                                    current_relevance = st.text_area("Nuværende relevans", c["current_relevance"] or "")
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE company_cases SET title=?, summary=?, significance=?, current_relevance=?, updated_at=? WHERE id=?",
                                            (title, summary, significance, current_relevance, now_iso(), int(c["id"]))); st.rerun()
                                    if b.form_submit_button("Slet sag"):
                                        run("DELETE FROM company_cases WHERE id=?", (int(c["id"]),)); st.rerun()
                with st.expander("Tilføj sag/historik"):
                    with st.form(f"add_case_{company_id}_{st.session_state.get('case_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        case_type = st.text_input("Sagstype", value="Myndighedsreaktion / GMP")
                        period_start = st.text_input("Periode start", value="")
                        period_end = st.text_input("Periode slut", value="")
                        severity = st.selectbox("Alvor", ["Lav","Middel","Høj","Kritisk"], index=2)
                        relevance = st.selectbox("Relevans", ["Lav","Middel","Høj","Kritisk"], index=1)
                        status = st.selectbox("Status", ["Åben","Afsluttet","Monitoreres","Arkiveret"], index=1)
                        summary = st.text_area("Kort resume", value="")
                        significance = st.text_area("Betydning", value="")
                        current_relevance = st.text_area("Nuværende relevans", value="")
                        if st.form_submit_button("Gem sag"):
                            run("""INSERT INTO company_cases (company_id, title, case_type, period_start, period_end, severity, relevance, status, summary, significance, current_relevance, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, title, case_type, period_start, period_end, severity, relevance, status, summary, significance, current_relevance, now_iso(), now_iso()))
                            st.session_state["case_form_version"] = st.session_state.get("case_form_version",0) + 1
                            st.rerun()

            elif section_base == "Kontakter":
                contacts = q("SELECT * FROM contacts WHERE company_id=? ORDER BY name", (company_id,))
                if len(contacts):
                    for _, c in contacts.iterrows():
                        with st.container(border=True):
                            col1, col2, col3 = st.columns([2.2, 2.2, 1.2])
                            col1.markdown(f"**{c['name']}**")
                            col2.caption(c["role"] or "")
                            if c["email"]:
                                col1.caption(c["email"])
                            if c["linkedin"]:
                                col2.markdown(f"[LinkedIn]({c['linkedin']})")
                            if c["notes"]:
                                st.caption(c["notes"])
                            with col3.expander("Ret/slet"):
                                with st.form(f"edit_contact_{int(c['id'])}"):
                                    name = st.text_input("Navn", c["name"])
                                    role = st.text_input("Rolle", c["role"] or "")
                                    email = st.text_input("Email", c["email"] or "")
                                    linkedin = st.text_input("LinkedIn", c["linkedin"] or "")
                                    notes = st.text_area("Noter", c["notes"] or "", height=90)
                                    if st.form_submit_button("Gem"):
                                        run("UPDATE contacts SET name=?, role=?, email=?, linkedin=?, notes=? WHERE id=?",
                                            (name, role, email, linkedin, notes, int(c["id"]))); st.rerun()
                                    if st.form_submit_button("Slet"):
                                        run("DELETE FROM contacts WHERE id=?", (int(c["id"]),)); st.rerun()
                else:
                    st.info("Ingen kontakter.")
                with st.expander("Tilføj kontakt"):
                    with st.form(f"add_contact_{company_id}_{st.session_state.get('contact_form_version',0)}", clear_on_submit=True):
                        name = st.text_input("Navn", value="")
                        role = st.text_input("Rolle", value="")
                        email = st.text_input("Email", value="")
                        linkedin = st.text_input("LinkedIn", value="")
                        notes = st.text_area("Noter", value="", height=90)
                        if st.form_submit_button("Gem kontakt"):
                            run("INSERT INTO contacts (company_id, name, role, email, linkedin, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (company_id, name, role, email, linkedin, notes, now_iso()))
                            st.session_state["contact_form_version"] = st.session_state.get("contact_form_version",0) + 1
                            st.rerun()

            elif section_base == "Noter":
                notes = q("SELECT * FROM notes WHERE company_id=? ORDER BY created_at DESC", (company_id,))
                if len(notes):
                    for _, n in notes.iterrows():
                        with st.container(border=True):
                            title = n["title"] if "title" in notes.columns and n["title"] else "Note"
                            st.markdown(f"**{title}**")
                            st.caption(f"Dato: {display_date(n['created_at'])}")
                            st.write(n["note"])
                            with st.expander("Redigér / slet note"):
                                with st.form(f"edit_note_{int(n['id'])}"):
                                    title2 = st.text_input("Overskrift", title if title != "Note" else "")
                                    note2 = st.text_area("Note", n["note"], height=160)
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE notes SET title=?, note=?, updated_at=? WHERE id=?", (title2, note2, now_iso(), int(n["id"]))); st.rerun()
                                    if b.form_submit_button("Slet note"):
                                        run("DELETE FROM notes WHERE id=?", (int(n["id"]),)); st.rerun()
                with st.expander("Tilføj note"):
                    with st.form(f"add_note_{company_id}_{st.session_state.get('note_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Overskrift", value="")
                        note = st.text_area("Note", value="", height=160)
                        if st.form_submit_button("Gem note"):
                            run("INSERT INTO notes (company_id, title, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                (company_id, title, note, now_iso(), now_iso()))
                            st.session_state["note_form_version"] = st.session_state.get("note_form_version",0) + 1
                            st.rerun()

            elif section_base == "Videnbank":
                memories = q("SELECT * FROM intelligence_memory WHERE company_id=? ORDER BY created_at DESC", (company_id,))
                if len(memories):
                    for _, m in memories.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{m['title'] or m['memory_type']}**")
                            st.caption(f"Dato: {display_date(m['created_at'])} · {m['memory_type']} · sikkerhed: {m['confidence']}")
                            st.write(m["content"])
                            with st.expander("Redigér / slet viden"):
                                with st.form(f"edit_mem_{int(m['id'])}"):
                                    title = st.text_input("Titel", m["title"] or "")
                                    content = st.text_area("Indhold", m["content"], height=180)
                                    confidence = st.selectbox("Sikkerhed", ["Lav","Middel","Høj"], index=severity_index(m["confidence"], ["Lav","Middel","Høj"]))
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE intelligence_memory SET title=?, content=?, confidence=?, updated_at=? WHERE id=?",
                                            (title, content, confidence, now_iso(), int(m["id"]))); st.rerun()
                                    if b.form_submit_button("Slet viden"):
                                        run("DELETE FROM intelligence_memory WHERE id=?", (int(m["id"]),)); st.rerun()
                with st.expander("Tilføj viden"):
                    with st.form(f"add_memory_{company_id}_{st.session_state.get('mem_form_version',0)}", clear_on_submit=True):
                        memory_type = st.selectbox("Type", ["Observation","Relation","Kultur","Regulatorisk modenhed","Historisk erfaring","Strategisk mulighed"])
                        title = st.text_input("Titel", value="")
                        content = st.text_area("Indhold", value="", height=180)
                        confidence = st.selectbox("Sikkerhed", ["Lav","Middel","Høj"], index=1)
                        if st.form_submit_button("Gem viden"):
                            run("INSERT INTO intelligence_memory (company_id, memory_type, title, content, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (company_id, memory_type, title, content, confidence, now_iso(), now_iso()))
                            st.session_state["mem_form_version"] = st.session_state.get("mem_form_version",0) + 1
                            st.rerun()

            elif section_base == "Briefing":
                st.markdown("### Briefing til kommende møde")
                st.markdown(f"**Virksomhed:** {row['name']}")
                saved_briefings = q(
                    """SELECT b.*, m.title AS meeting_title, m.meeting_date, m.meeting_time
                       FROM briefings b
                       LEFT JOIN meetings m ON m.id=b.meeting_id
                       WHERE b.company_id=?
                       ORDER BY b.created_at DESC, b.id DESC""",
                    (company_id,),
                )
                if len(saved_briefings):
                    st.markdown("### Gemte briefings")
                    for _, b in saved_briefings.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{b['title']}**")
                            st.caption(f"Oprettet: {display_date(b['created_at'])} · version {int(b['version'] or 1)} · {b['status']}")
                            if b["meeting_id"]:
                                meeting_label = display_date(b["meeting_date"]) or "Ukendt dato"
                                if b["meeting_time"]:
                                    meeting_label += f" kl. {b['meeting_time']}"
                                st.caption(f"Knyttet til møde: {meeting_label} - {b['meeting_title'] or 'Møde'}")
                            st.markdown(b["briefing_text"])
                            if b["user_notes"]:
                                st.markdown("**Egne noter**")
                                st.write(b["user_notes"])
                            with st.expander("Redigér / slet briefing"):
                                with st.form(f"edit_briefing_{int(b['id'])}"):
                                    title = st.text_input("Titel", b["title"])
                                    labels, values, selected_index = meeting_options(company_id, b["meeting_id"])
                                    selected_meeting = st.selectbox("Knyttet til møde", labels, index=selected_index)
                                    briefing_text = st.text_area("Briefing", b["briefing_text"], height=260)
                                    user_notes = st.text_area("Egne noter", b["user_notes"] or "", height=120)
                                    status = st.selectbox("Status", ["Aktiv", "Arkiveret"], index=severity_index(b["status"], ["Aktiv", "Arkiveret"]))
                                    a, c = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run(
                                            "UPDATE briefings SET title=?, meeting_id=?, briefing_text=?, user_notes=?, status=?, updated_at=? WHERE id=?",
                                            (title, values[selected_meeting], briefing_text, user_notes, status, now_iso(), int(b["id"])),
                                        )
                                        st.rerun()
                                    if c.form_submit_button("Slet briefing"):
                                        run("DELETE FROM briefings WHERE id=?", (int(b["id"]),))
                                        st.rerun()
                else:
                    st.info("Ingen gemte briefings endnu. Brug Briefing-generatoren og gem et udkast.")

                recent_meetings = q("SELECT meeting_date, meeting_time, location, title, key_takeaways, next_steps FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC LIMIT 5", (company_id,))
                recent_obs = q("SELECT observation_date, title, observation_type, confidence, verification_status FROM observations WHERE company_id=? ORDER BY observation_date DESC, created_at DESC LIMIT 8", (company_id,))
                if len(recent_meetings):
                    st.markdown("**Seneste møder:**")
                    for _, m in recent_meetings.iterrows():
                        when = display_date(m["meeting_date"])
                        if m["meeting_time"]: when += f" kl. {m['meeting_time']}"
                        loc = f" ({m['location']})" if m["location"] else ""
                        st.markdown(f"- {when}: {m['title']}{loc} — {m['key_takeaways'] or ''} {m['next_steps'] or ''}")
                if len(recent_obs):
                    st.markdown("**Observationer:**")
                    for _, o in recent_obs.iterrows():
                        st.markdown(f"- {display_date(o['observation_date'])}: {o['title']} ({o['observation_type']}, {o['confidence']}, {o['verification_status']})")
                st.markdown("**Mulige dagsordenpunkter:**")
                st.markdown("- Opfølgning på tidligere aftaler og åbne punkter")
                st.markdown("- Nye observationer, der bør verificeres")
                st.markdown("- Relevante regulatoriske/kvalitetsmæssige temaer")
                st.markdown("- Eventuelle frister, næste skridt og mulige rådgivningsbehov")

elif page == "Møder & referater":
    st.subheader("Møder & referater")
    df = q("""SELECT m.id, m.meeting_date AS dato, m.meeting_time AS tid, m.location AS sted, c.name AS virksomhed, m.title AS titel,
                     m.meeting_type AS type, m.participants AS deltagere, m.summary AS resume,
                     m.key_takeaways AS læring, m.next_steps AS næste_skridt,
                     m.uploaded_filename AS filnavn, m.raw_text AS referattekst
              FROM meetings m LEFT JOIN companies c ON c.id=m.company_id
              ORDER BY m.meeting_date DESC, m.meeting_time DESC, m.created_at DESC""")
    if len(df):
        table_df = df.drop(columns=["id", "referattekst"])
        st.dataframe(table_df, use_container_width=True, hide_index=True)
        with st.expander("Åbn referat / mødedetaljer", expanded=False):
            options = []
            for _, row in df.iterrows():
                label = f"{display_date(row['dato'])} - {row['virksomhed']} - {row['titel']}"
                options.append((label, int(row["id"])))
            selected_label = st.selectbox("Vælg møde", [label for label, _ in options])
            selected_id = dict(options)[selected_label]
            selected = df[df["id"] == selected_id].iloc[0]
            if selected["filnavn"]:
                st.caption(f"Uploadet fil: {selected['filnavn']}")
            if selected["resume"]:
                st.markdown("**Resume**")
                st.write(selected["resume"])
            if selected["læring"]:
                st.markdown("**Hvad lærte vi**")
                st.write(selected["læring"])
            if selected["næste_skridt"]:
                st.markdown("**Næste skridt / frister**")
                st.write(selected["næste_skridt"])
            if selected["referattekst"]:
                st.markdown("**Referattekst**")
                st.text_area("Referattekst", selected["referattekst"], height=360, key=f"meeting_page_raw_text_{selected_id}")
            else:
                st.info("Der er ikke gemt referattekst på dette møde.")
    else:
        st.info("Ingen møder endnu.")

elif page == "Observationer":
    st.subheader("Observationer")
    df = q("""SELECT o.observation_date AS dato, c.name AS virksomhed, o.title AS titel, o.observation_type AS type,
                     o.source_type AS kilde, o.confidence AS tillid, o.verification_status AS verifikation,
                     o.implication AS betydning, o.follow_up AS opfølgning
              FROM observations o LEFT JOIN companies c ON c.id=o.company_id
              ORDER BY o.observation_date DESC, o.created_at DESC""")
    if len(df):
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen observationer endnu.")

elif page == "Briefing":
    st.subheader("Briefing-generator")
    companies = q("SELECT id, name FROM companies ORDER BY name")
    if len(companies):
        company_ids = companies["id"].tolist()
        default_id = st.session_state.get("selected_company_id", company_ids[0])
        default_index = company_ids.index(default_id) if default_id in company_ids else 0
        selected = st.selectbox("Virksomhed", companies["name"].tolist(), index=default_index)
        cid = int(companies[companies["name"] == selected]["id"].iloc[0])
        st.session_state["selected_company_id"] = cid
        st.markdown(f"## Briefing: {selected}")

        latest_id = latest_meeting_id(cid)
        preferred_meeting_id = st.session_state.get("selected_briefing_meeting_id", latest_id)
        if preferred_meeting_id and not len(q("SELECT id FROM meetings WHERE company_id=? AND id=?", (cid, int(preferred_meeting_id)))):
            preferred_meeting_id = latest_id
        labels, values, selected_index = meeting_options(cid, preferred_meeting_id)
        selected_meeting = st.selectbox("Møde der forberedes", labels, index=selected_index)
        selected_meeting_id = values[selected_meeting]
        st.session_state["selected_briefing_meeting_id"] = selected_meeting_id

        context = briefing_context(cid) + meeting_focus_context(cid, selected_meeting_id)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("### Datagrundlag")
            for heading, sql in [
                ("Seneste møder", "SELECT meeting_date AS dato, meeting_time AS tid, location AS sted, title AS titel, key_takeaways AS læring, next_steps AS næste_skridt FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC LIMIT 5"),
                ("Observationer", "SELECT observation_date AS dato, title AS titel, observation_type AS type, confidence AS tillid, verification_status AS verifikation FROM observations WHERE company_id=? ORDER BY observation_date DESC LIMIT 8"),
                ("Historik / sager", "SELECT title AS titel, case_type AS type, severity AS alvor, relevance AS relevans, summary AS resume FROM company_cases WHERE company_id=? ORDER BY period_start DESC LIMIT 5"),
                ("Signaler", "SELECT collected_at AS dato, title AS titel, trigger_type AS trigger, score AS score FROM signals WHERE company_id=? ORDER BY collected_at DESC LIMIT 8")
            ]:
                df = q(sql, (cid,))
                if len(df):
                    st.markdown(f"**{heading}**")
                    st.dataframe(df, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("### Udkast til mødeforberedelse")
            if st.button("Generér briefing"):
                st.session_state[f"generated_briefing_{cid}_{selected_meeting_id or 'none'}"] = ai_briefing_text(selected, context)
            generated_key = f"generated_briefing_{cid}_{selected_meeting_id or 'none'}"
            if generated_key in st.session_state:
                briefing_text = st.session_state[generated_key]
                st.markdown(briefing_text)
                with st.form(f"save_briefing_{cid}"):
                    default_title = f"Briefing - {selected} - {datetime.now().strftime('%Y-%m-%d')}"
                    title = st.text_input("Titel", default_title)
                    user_notes = st.text_area("Egne noter", value="", height=120)
                    if st.form_submit_button("Gem briefing på virksomheden"):
                        existing = q("SELECT MAX(version) AS max_version FROM briefings WHERE company_id=?", (cid,))
                        max_version = int(existing["max_version"].iloc[0] or 0) if len(existing) else 0
                        run(
                            """INSERT INTO briefings
                               (company_id, meeting_id, title, briefing_text, user_notes, source_context, version, status, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                cid,
                                selected_meeting_id,
                                title,
                                briefing_text,
                                user_notes,
                                context,
                                max_version + 1,
                                "Aktiv",
                                now_iso(),
                                now_iso(),
                            ),
                        )
                        st.success("Briefing gemt på virksomhedsprofilen.")
            else:
                st.caption("Tryk på knappen for at danne et udkast. Hvis OpenAI API-nøgle ikke er sat, laves en lokal struktureret briefing.")

        with st.expander("Rå kontekst brugt til briefing"):
            st.text_area("Kontekst", context, height=300)

elif page == "Kilder":
    st.subheader("Kildeadministration")
    df = q("SELECT id, name AS navn, source_type AS type, url, keywords AS nøgleord, status, priority AS prioritet, last_checked AS sidst_tjekket, last_error AS seneste_fejl FROM sources ORDER BY status, priority DESC, name")
    if len(df):
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen kilder.")
    with st.expander("Tilføj kilde"):
        with st.form("add_source_form", clear_on_submit=True):
            name = st.text_input("Navn")
            source_type = st.text_input("Type")
            url = st.text_input("URL")
            keywords = st.text_input("Nøgleord")
            status = st.selectbox("Status", ["Aktiv","Pauset"], index=0)
            priority = st.selectbox("Prioritet", ["Lav","Middel","Høj"], index=1)
            if st.form_submit_button("Gem kilde"):
                run("INSERT INTO sources (name, source_type, url, keywords, status, priority) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, source_type, url, keywords, status, priority))
                st.rerun()

    if len(df):
        st.markdown("### Redigér / slet kilder")
        for _, r in df.iterrows():
            with st.expander(f"{r['navn']}"):
                with st.form(f"edit_source_{int(r['id'])}"):
                    name = st.text_input("Navn", r["navn"])
                    source_type = st.text_input("Type", r["type"] or "")
                    url = st.text_input("URL", r["url"] or "")
                    keywords = st.text_input("Nøgleord", r["nøgleord"] or "")
                    status = st.selectbox("Status", ["Aktiv","Pauset"], index=0 if r["status"]=="Aktiv" else 1)
                    priority = st.selectbox("Prioritet", ["Lav","Middel","Høj"], index=["Lav","Middel","Høj"].index(r["prioritet"]) if r["prioritet"] in ["Lav","Middel","Høj"] else 1)
                    if st.form_submit_button("Gem ændringer"):
                        run("UPDATE sources SET name=?, source_type=?, url=?, keywords=?, status=?, priority=? WHERE id=?",
                            (name, source_type, url, keywords, status, priority, int(r["id"])))
                        st.rerun()
                    if st.form_submit_button("Slet kilde"):
                        run("DELETE FROM sources WHERE id=?", (int(r["id"]),))
                        st.rerun()

elif page == "Triggerregler":
    st.subheader("Triggerregler")
    df = q("SELECT id, name AS navn, pattern AS mønster, default_score AS score, weight AS vægt, active AS aktiv FROM trigger_rules ORDER BY weight DESC")
    if len(df):
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen triggerregler.")
    with st.expander("Tilføj triggerregel"):
        with st.form("add_trigger_form", clear_on_submit=True):
            name = st.text_input("Navn")
            pattern = st.text_input("Mønster")
            score = st.selectbox("Score", ["Lav","Middel","Høj","Kritisk"], index=1)
            weight = st.number_input("Vægt", value=5)
            active = st.checkbox("Aktiv", value=True)
            if st.form_submit_button("Gem triggerregel"):
                run("INSERT INTO trigger_rules (name, pattern, default_score, weight, active) VALUES (?, ?, ?, ?, ?)",
                    (name, pattern, score, weight, 1 if active else 0))
                st.rerun()

    if len(df):
        st.markdown("### Redigér / slet triggerregler")
        for _, r in df.iterrows():
            with st.expander(f"{r['navn']}"):
                with st.form(f"edit_trigger_{int(r['id'])}"):
                    name = st.text_input("Navn", r["navn"])
                    pattern = st.text_input("Mønster", r["mønster"] or "")
                    score = st.selectbox("Score", ["Lav","Middel","Høj","Kritisk"], index=["Lav","Middel","Høj","Kritisk"].index(r["score"]) if r["score"] in ["Lav","Middel","Høj","Kritisk"] else 1)
                    weight = st.number_input("Vægt", value=int(r["vægt"]) if r["vægt"] else 5)
                    active = st.checkbox("Aktiv", value=bool(r["aktiv"]))
                    if st.form_submit_button("Gem ændringer"):
                        run("UPDATE trigger_rules SET name=?, pattern=?, default_score=?, weight=?, active=? WHERE id=?",
                            (name, pattern, score, weight, 1 if active else 0, int(r["id"])))
                        st.rerun()
                    if st.form_submit_button("Slet triggerregel"):
                        run("DELETE FROM trigger_rules WHERE id=?", (int(r["id"]),))
                        st.rerun()
