from datetime import date, datetime, timedelta


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


def has_db_id(value):
    return str(value or "").strip().lower() not in ("", "none", "nan")


def clean_text_value(value):
    text = str(value or "").strip()
    return "" if text.lower() == "nan" else text


def merge_text_values(primary_value, secondary_value, secondary_label):
    primary_text = clean_text_value(primary_value)
    secondary_text = clean_text_value(secondary_value)
    if not secondary_text:
        return primary_text
    if not primary_text:
        return secondary_text
    if secondary_text in primary_text:
        return primary_text
    return f"{primary_text}\n\n---\n{secondary_label}\n{secondary_text}"


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


def followup_due_label(due_value, today_iso=None):
    due = str(due_value or "").strip()
    if not due:
        return "Ingen dato"
    shown = display_date(due)
    if len(due) >= 10 and due[4:5] == "-" and due[7:8] == "-":
        try:
            today_date = date.fromisoformat(today_iso or date.today().isoformat())
            due_date = date.fromisoformat(due[:10])
            days = (due_date - today_date).days
            if days < 0:
                return f"{shown} · {abs(days)} dage for sent"
            if days == 0:
                return f"{shown} · i dag"
            if days == 1:
                return f"{shown} · i morgen"
            return f"{shown} · om {days} dage"
        except ValueError:
            pass
    return shown
