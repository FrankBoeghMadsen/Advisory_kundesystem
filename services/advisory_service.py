from repositories import q, run
from ui.formatting import display_date, field_label, now_iso


def sync_actor_sources(actor_name, website, linkedin, aliases="", actor_status="Aktiv"):
    keywords = "|".join([part for part in [actor_name, aliases] if part])
    source_status = "Aktiv" if actor_status == "Aktiv" else "Pauset"
    for label, url, source_type, status, active in [
        ("Website", website, "web", source_status, 1 if source_status == "Aktiv" else 0),
        ("LinkedIn", linkedin, "reference", "Pauset", 0),
    ]:
        clean_url = (url or "").strip()
        if not clean_url:
            continue
        existing = q("SELECT id FROM sources WHERE url=?", (clean_url,))
        if len(existing):
            continue
        run(
            """INSERT INTO sources
               (name, source_type, url, keywords, active, status, priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"{actor_name} - {label}", source_type, clean_url, keywords, active, status, "Høj" if label == "LinkedIn" else "Middel", now_iso()),
        )


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
        q("""SELECT created_at, due_date, title, followup_type, description, next_action, person, priority, status, source_type
             FROM followups WHERE company_id=?""", (company_id,)),
        "Opfølgning",
        "due_date",
        "title",
        ["next_action", "description"],
        ["followup_type", "person", "priority", "status", "source_type"],
    )
    return sorted(items, key=lambda item: item["sort_date"] or "", reverse=True)


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
        ("Åbne opfølgninger / leads", "SELECT due_date, title, followup_type, next_action, description, person, priority, status, source_type FROM followups WHERE company_id=? AND COALESCE(status,'Ny') NOT IN ('Lukket','Arkiveret') ORDER BY due_date ASC, created_at DESC LIMIT 15"),
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
