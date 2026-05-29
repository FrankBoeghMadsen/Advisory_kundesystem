from db import connect, insert_signal
from connectors import fetch_source, extract_context_from_url
from analysis_engine import analyze_signal

def load_rows(conn, table):
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]

def match_company(item, companies):
    text = f"{item.get('title','')} {item.get('raw_summary','')}".lower()
    best = None
    for c in companies:
        aliases = [c["name"]]
        # Practical alias simplification + user-defined aliases.
        aliases.append(c["name"].replace(" A/S","").replace(" ApS","").replace(" group",""))
        if c.get("aliases"):
            aliases.extend([a.strip() for a in c["aliases"].split("|") if a.strip()])
        for alias in aliases:
            if alias and alias.lower() in text:
                return c
    return best

def run_monitor():
    with connect() as conn:
        sources = [dict(r) for r in conn.execute("SELECT * FROM sources WHERE active=1 AND COALESCE(status,'Aktiv')='Aktiv'")]
        companies = [dict(r) for r in conn.execute("SELECT * FROM companies WHERE status='Aktiv'")]
        rules = [dict(r) for r in conn.execute("SELECT * FROM trigger_rules WHERE active=1")]
    collected = 0
    relevant = 0
    for source in sources:
        try:
            items = fetch_source(source)
            with connect() as conn:
                conn.execute("UPDATE sources SET last_checked=?, last_error='' WHERE id=?", (__import__('datetime').datetime.utcnow().isoformat(), source["id"]))
                conn.commit()
        except Exception as e:
            with connect() as conn:
                conn.execute("UPDATE sources SET last_checked=?, last_error=? WHERE id=?", (__import__('datetime').datetime.utcnow().isoformat(), str(e)[:500], source["id"]))
                conn.commit()
            continue
        collected += len(items)
        for item in items:
            company = match_company(item, companies)
            search_text = f"{item['title']}\n{item.get('raw_summary','')}"
            # Keep item if company is mentioned OR source keywords are strong enough.
            if not company:
                continue
            terms = [company["name"]]
            if company.get("aliases"):
                terms.extend([a.strip() for a in company["aliases"].split("|") if a.strip()])
            for rule in rules:
                if rule.get("pattern"):
                    terms.extend([p.strip() for p in rule["pattern"].split("|")[:4] if len(p.strip()) > 2])
            context = extract_context_from_url(item.get("url", ""), terms)
            if context.get("excerpt"):
                item["source_excerpt"] = context["excerpt"]
                item["matched_terms"] = context.get("matched_terms", "")
                search_text = f"{search_text}\n\nKildeuddrag:\n{context['excerpt']}"
            analysis = analyze_signal(search_text, company["name"], rules)
            item.update(analysis)
            item["company_id"] = company["id"]
            insert_signal(item)
            relevant += 1
    return {"collected": collected, "relevant": relevant}